# backend/app/services/document_service.py
"""
Document service for file handling and processing.
"""

import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentType, DocumentStatus
from app.models.claim import Claim
from app.core.config import settings
from app.core.exceptions import (
    ResourceNotFoundError,
    DocumentProcessingError,
    ValidationError
)
from app.ingestion.pdf_parser import PDFParser
from app.ingestion.ocr_processor import OCRProcessor
from app.ingestion.medical_extractor import MedicalExtractor
from app.ingestion.clause_split import ClauseSplitter
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for document upload, storage, and processing.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        endpoint_url = None
        if settings.USE_LOCALSTACK:
            endpoint_url = settings.S3_ENDPOINT_URL or settings.AWS_ENDPOINT_URL

        logger.info(
            "Initializing S3 client (use_localstack=%s, endpoint_url=%s)",
            settings.USE_LOCALSTACK,
            endpoint_url if endpoint_url else "aws-default",
        )

        self.s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=endpoint_url
        )
        self.pdf_parser = PDFParser()
        self.ocr_processor = OCRProcessor()
        self.medical_extractor = MedicalExtractor()
        self.clause_splitter = ClauseSplitter()
        self.embedding_service: Optional[EmbeddingService] = None

    def _extract_s3_error(self, error: ClientError) -> tuple[str, str]:
        payload = getattr(error, "response", {}) or {}
        error_data = payload.get("Error", {}) or {}
        code = str(error_data.get("Code", "UnknownError"))
        message = str(error_data.get("Message", "S3 operation failed"))
        return code, message

    def _ensure_bucket_exists(self) -> None:
        bucket = settings.S3_BUCKET_NAME
        try:
            self.s3_client.head_bucket(Bucket=bucket)
            return
        except ClientError as error:
            code, message = self._extract_s3_error(error)
            missing_bucket_codes = {"404", "NoSuchBucket", "NotFound"}
            access_denied_codes = {"403", "AccessDenied", "Forbidden"}
            if code in missing_bucket_codes and settings.USE_LOCALSTACK:
                logger.warning(
                    "S3 bucket '%s' missing in localstack; attempting auto-create", bucket
                )
                try:
                    create_params = {"Bucket": bucket}
                    if settings.AWS_REGION and settings.AWS_REGION != "us-east-1":
                        create_params["CreateBucketConfiguration"] = {
                            "LocationConstraint": settings.AWS_REGION
                        }
                    self.s3_client.create_bucket(**create_params)
                    logger.info("Created localstack S3 bucket '%s'", bucket)
                    return
                except ClientError as create_error:
                    create_code, create_message = self._extract_s3_error(create_error)
                    if create_code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                        raise DocumentProcessingError(
                            f"Storage bucket initialization failed ({create_code}): {create_message}"
                        )
                    return

            if code in missing_bucket_codes:
                raise DocumentProcessingError(
                    f"Storage bucket '{bucket}' was not found in region '{settings.AWS_REGION}'"
                )

            if code in access_denied_codes:
                logger.warning(
                    "head_bucket access denied for bucket '%s' (code=%s); proceeding to object upload check",
                    bucket,
                    code,
                )
                return

            raise DocumentProcessingError(
                f"Storage bucket access failed ({code}): {message}"
            )

    def upload_bytes(self, s3_key: str, content: bytes, content_type: str) -> None:
        """Upload bytes to S3 with robust storage diagnostics."""
        self._ensure_bucket_exists()
        try:
            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
            )
        except ClientError as error:
            code, message = self._extract_s3_error(error)
            if code in {"403", "AccessDenied", "Forbidden"}:
                raise DocumentProcessingError(
                    "Storage upload failed (403): Access denied. "
                    "Ensure IAM policy 'ClaimLensS3AccessPolicy' allows "
                    f"s3:PutObject,s3:GetObject,s3:DeleteObject on bucket '{settings.S3_BUCKET_NAME}'"
                )
            raise DocumentProcessingError(f"Storage upload failed ({code}): {message}")

    def get_storage_diagnostics(self) -> Dict[str, Any]:
        """Run lightweight S3 permission checks for current configuration."""
        bucket = settings.S3_BUCKET_NAME
        test_key = f"diagnostics/storage-check-{uuid4().hex}.txt"
        payload = b"claimlens-storage-check"

        checks: Dict[str, Dict[str, Any]] = {
            "head_bucket": {"ok": False, "detail": None},
            "put_object": {"ok": False, "detail": None},
            "get_object": {"ok": False, "detail": None},
            "delete_object": {"ok": False, "detail": None},
        }

        try:
            self.s3_client.head_bucket(Bucket=bucket)
            checks["head_bucket"] = {"ok": True, "detail": "Bucket is reachable"}
        except ClientError as error:
            code, message = self._extract_s3_error(error)
            checks["head_bucket"] = {
                "ok": False,
                "detail": f"{code}: {message}",
            }

        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=test_key,
                Body=payload,
                ContentType="text/plain",
            )
            checks["put_object"] = {"ok": True, "detail": f"Uploaded test object: {test_key}"}
        except ClientError as error:
            code, message = self._extract_s3_error(error)
            checks["put_object"] = {"ok": False, "detail": f"{code}: {message}"}

        if checks["put_object"]["ok"]:
            try:
                response = self.s3_client.get_object(Bucket=bucket, Key=test_key)
                body = response["Body"].read()
                if body == payload:
                    checks["get_object"] = {"ok": True, "detail": "Downloaded test object successfully"}
                else:
                    checks["get_object"] = {
                        "ok": False,
                        "detail": "Downloaded test object did not match uploaded payload",
                    }
            except ClientError as error:
                code, message = self._extract_s3_error(error)
                checks["get_object"] = {"ok": False, "detail": f"{code}: {message}"}

            try:
                self.s3_client.delete_object(Bucket=bucket, Key=test_key)
                checks["delete_object"] = {"ok": True, "detail": "Deleted test object successfully"}
            except ClientError as error:
                code, message = self._extract_s3_error(error)
                checks["delete_object"] = {"ok": False, "detail": f"{code}: {message}"}

        object_ops_ok = (
            checks["put_object"]["ok"]
            and checks["get_object"]["ok"]
            and checks["delete_object"]["ok"]
        )

        return {
            "success": object_ops_ok,
            "bucket": bucket,
            "region": settings.AWS_REGION,
            "use_localstack": settings.USE_LOCALSTACK,
            "checks": checks,
            "message": (
                "Storage access is healthy"
                if object_ops_ok
                else "Storage access has permission/configuration issues"
            ),
        }

    async def generate_upload_url(
        self,
        claim_id: UUID,
        document_type: DocumentType,
        filename: str,
        content_type: str,
        file_size: int
    ) -> tuple[Document, str]:
        """
        Generate presigned URL for document upload.

        Args:
            claim_id: Claim ID
            document_type: Type of document
            filename: Original filename
            content_type: MIME type
            file_size: File size in bytes

        Returns:
            Tuple of (document record, presigned URL)
        """
        # Validate file size
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise ValidationError(
                f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Generate S3 key
        s3_key = f"claims/{claim_id}/{document_type.value}/{filename}"

        # Create document record
        document = Document(
            claim_id=claim_id,
            document_type=document_type,
            filename=filename,
            s3_key=s3_key,
            file_size=file_size,
            content_type=content_type,
            status=DocumentStatus.UPLOADED
        )

        self.db.add(document)
        await self.db.flush()

        # Generate presigned URL
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": s3_key,
                    "ContentType": content_type
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRY
            )
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise DocumentProcessingError("Failed to generate upload URL")

        logger.info(f"Generated upload URL for document {document.id}")
        return document, presigned_url

    async def process_document(self, document_id: UUID) -> Document:
        """
        Process an uploaded document.

        Args:
            document_id: Document ID

        Returns:
            Processed document
        """
        document = await self.get_document(document_id)

        if document.status == DocumentStatus.PROCESSING:
            raise ValidationError("Document is still processing")

        if document.status == DocumentStatus.PROCESSED:
            raise ValidationError("Document is already processed")

        if document.status not in [DocumentStatus.UPLOADED, DocumentStatus.FAILED]:
            raise ValidationError(
                f"Document is in {document.status.value} state")

        document.status = DocumentStatus.PROCESSING
        await self.db.flush()

        try:
            # Download document from S3
            content = await self._download_from_s3(document.s3_key)
        # backend/app/services/document_service.py (continued)

            # Extract text based on document type
            if document.content_type == "application/pdf":
                extracted_text = await self.pdf_parser.extract_text(content)

                # If PDF is image-based, use OCR
                if not extracted_text or len(extracted_text.strip()) < 100:
                    logger.info(f"Using OCR for document {document_id}")
                    extracted_text = await self.ocr_processor.process_document(content)

            elif document.content_type == "application/json":
                extracted_text = content.decode("utf-8")

            else:
                raise DocumentProcessingError(
                    f"Unsupported content type: {document.content_type}"
                )

            document.extracted_text = extracted_text

            # Process based on document type
            if document.document_type == DocumentType.INSURANCE_POLICY:
                await self._process_policy_document(document, extracted_text)

            document.status = DocumentStatus.PROCESSED
            await self.db.flush()

            logger.info(f"Successfully processed document {document_id}")
            return document

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            try:
                await self.db.rollback()
                failed_document = await self.get_document(document_id)
                failed_document.status = DocumentStatus.FAILED
                await self.db.flush()
            except Exception as status_error:
                logger.error(
                    f"Failed to persist FAILED status for document {document_id}: {status_error}"
                )
                await self.db.rollback()
            raise DocumentProcessingError(f"Processing failed: {str(e)}")

    async def _process_policy_document(
        self,
        document: Document,
        text: str
    ) -> None:
        """
        Process insurance policy document - split into clauses and generate embeddings.
        """
        # Split into clauses
        clauses = await self.clause_splitter.split_document(
            text=text,
            document_id=str(document.id)
        )

        if not clauses:
            logger.warning(
                f"No structured clauses extracted from document {document.id}; using paragraph fallback chunking"
            )
            fallback_chunks = self._fallback_policy_chunks(text)
            if not fallback_chunks:
                logger.warning(f"No fallback chunks extracted from document {document.id}")
                return

            embeddings = await self._generate_policy_embeddings(
                texts=fallback_chunks,
                document_id=document.id,
            )

            vector_store = VectorStore(self.db)
            await vector_store.store_embeddings(
                document_id=document.id,
                chunks=fallback_chunks,
                embeddings=embeddings
            )

            logger.info(
                f"Stored {len(embeddings)} fallback embeddings for policy document {document.id}"
            )
            return

        # Generate embeddings for each clause
        clause_texts = [clause.content for clause in clauses]
        embeddings = await self._generate_policy_embeddings(
            texts=clause_texts,
            document_id=document.id,
        )

        # Store embeddings
        vector_store = VectorStore(self.db)
        await vector_store.store_embeddings(
            document_id=document.id,
            chunks=clause_texts,
            embeddings=embeddings
        )

        logger.info(
            f"Stored {len(embeddings)} embeddings for policy document {document.id}")

    async def _generate_policy_embeddings(
        self,
        texts: List[str],
        document_id: UUID,
    ) -> List[List[float]]:
        """Generate embeddings with resilient fallback chain for policy processing.

        Order:
        1) current configured embedding service
        2) forced local embedding service
        3) forced mock embedding service
        """
        if not texts:
            return []

        try:
            if self.embedding_service is None:
                self.embedding_service = get_embedding_service()

            embeddings = await self.embedding_service.generate_embeddings_batch(
                texts=texts,
                batch_size=10,
            )
            logger.info(
                "Generated embeddings for document %s using mode=%s",
                document_id,
                getattr(self.embedding_service, "mode", "unknown"),
            )
            return embeddings
        except Exception as primary_error:
            logger.warning(
                "Primary embedding generation failed for document %s (mode=%s): %s",
                document_id,
                getattr(self.embedding_service, "mode", "unknown"),
                primary_error,
            )

        for fallback_mode in ["local", "mock"]:
            try:
                fallback_service = get_embedding_service(force_mode=fallback_mode)
                embeddings = await fallback_service.generate_embeddings_batch(
                    texts=texts,
                    batch_size=10,
                )
                logger.warning(
                    "Using fallback embedding mode=%s for document %s",
                    fallback_mode,
                    document_id,
                )
                self.embedding_service = fallback_service
                return embeddings
            except Exception as fallback_error:
                logger.warning(
                    "Fallback embedding mode=%s failed for document %s: %s",
                    fallback_mode,
                    document_id,
                    fallback_error,
                )

        raise DocumentProcessingError(
            "Embedding generation failed across all modes (bedrock/local/mock)"
        )

    def _fallback_policy_chunks(self, text: str, max_words: int = 160) -> List[str]:
        """Fallback chunking for policy text when structured clause splitting yields no results."""
        normalized = (text or "").strip()
        if not normalized:
            return []

        noise_patterns = [
            r"^\[\s*page\s*\d+\s*\]$",
            r"^page\s*\d+$",
            r"^uin\s*:",
            r"^policy\s+version\s+year\s*:",
            r"^insurer\s*:",
            r"^policy\s+wording(?:\s*\(.*\))?$",
        ]

        cleaned_lines = []
        for raw_line in normalized.splitlines():
            line = re.sub(r"\s+", " ", raw_line.replace("\u200b", " ").replace("\ufeff", " ")).strip()
            if not line:
                continue
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in noise_patterns):
                continue
            cleaned_lines.append(line)

        normalized = "\n".join(cleaned_lines).strip()
        if not normalized:
            return []

        paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n+", normalized)
            if p and p.strip()
        ]

        chunks: List[str] = []
        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                continue
            if len(words) <= max_words:
                chunks.append(paragraph)
                continue

            start = 0
            while start < len(words):
                end = min(start + max_words, len(words))
                chunk = " ".join(words[start:end]).strip()
                if chunk:
                    chunks.append(chunk)
                start = end

        return chunks[:200]

    async def get_document(self, document_id: UUID) -> Document:
        """Get document by ID."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ResourceNotFoundError("Document", document_id)

        return document

    async def get_claim_documents(
        self,
        claim_id: UUID,
        document_type: Optional[DocumentType] = None
    ) -> List[Document]:
        """Get all documents for a claim."""
        query = select(Document).where(Document.claim_id == claim_id)

        if document_type:
            query = query.where(Document.document_type == document_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_download_url(self, document_id: UUID) -> str:
        """Generate presigned URL for document download."""
        document = await self.get_document(document_id)

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": document.s3_key
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRY
            )
            return presigned_url
        except ClientError as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise DocumentProcessingError("Failed to generate download URL")

    async def _download_from_s3(self, s3_key: str) -> bytes:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key
            )
            return response["Body"].read()
        except ClientError as e:
            logger.error(f"S3 download failed: {str(e)}")
            raise DocumentProcessingError(f"Failed to download file: {str(e)}")

    async def delete_document(self, document_id: UUID) -> None:
        """Delete document and its S3 object."""
        document = await self.get_document(document_id)

        # Delete from S3
        try:
            self.s3_client.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=document.s3_key
            )
        except ClientError as e:
            logger.warning(f"Failed to delete S3 object: {str(e)}")

        # Delete embeddings
        vector_store = VectorStore(self.db)
        await vector_store.delete_document_embeddings(document_id)

        # Delete document record
        await self.db.delete(document)
        await self.db.flush()

        logger.info(f"Deleted document {document_id}")
