# backend/app/api/v1/endpoints/documents.py
"""
Document management endpoints.
"""

from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, status, UploadFile, File, Form, HTTPException
import logging

from app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
    DocumentTextResponse
)
from app.schemas.common import SingleResponse
from app.models.document import DocumentType, Document, DocumentStatus
from app.models.claim import Claim, ClaimStatus
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.claim_service import ClaimService
from app.api.deps import (
    get_document_service,
    get_claim_service,
    get_current_user
)
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.config import settings
from app.core.exceptions import DocumentProcessingError
from app.ingestion.pdf_parser import PDFParser


router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)


INSURANCE_POLICY_KEYWORDS = {
    "insurance", "policy", "coverage", "claim", "sum insured",
    "premium", "exclusion", "waiting period", "hospitalization",
    "benefit", "deductible", "co-pay", "cashless", "network hospital",
}


def _looks_like_insurance_policy(text: str) -> bool:
    normalized = (text or "").lower()
    if len(normalized.strip()) < 200:
        return False

    matches = sum(
        1 for token in INSURANCE_POLICY_KEYWORDS if token in normalized)
    return matches >= 3


class UploadRequest(BaseModel):
    """Request body for upload URL generation."""
    claim_id: UUID
    document_type: DocumentType
    filename: str
    content_type: str
    file_size: int


@router.post(
    "/upload-url",
    response_model=DocumentUploadResponse,
    summary="Get upload URL"
)
async def get_upload_url(
    request: UploadRequest,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    Generate a presigned URL for document upload.

    The client should use the returned URL to upload the file directly to S3.
    """
    # Verify claim access
    await claim_service.get_claim(request.claim_id, current_user)

    document, upload_url = await document_service.generate_upload_url(
        claim_id=request.claim_id,
        document_type=request.document_type,
        filename=request.filename,
        content_type=request.content_type,
        file_size=request.file_size
    )

    return DocumentUploadResponse(
        document_id=document.id,
        upload_url=upload_url,
        expires_in=43200
    )


@router.get(
    "/storage-health",
    response_model=dict,
    summary="Check storage bucket permissions"
)
async def get_storage_health(
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Run storage diagnostics for current bucket configuration.

    Checks: head bucket, put/get/delete test object.
    """
    return document_service.get_storage_diagnostics()


@router.post(
    "/upload-direct",
    response_model=dict,
    summary="Upload document directly via backend"
)
async def upload_document_direct(
    claim_id: UUID = Form(...),
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    claim_service: ClaimService = Depends(get_claim_service),
):
    """
    Upload document content through backend and store in S3 server-side.

    This avoids browser-to-S3 CORS/preflight issues with presigned URLs.
    """
    await claim_service.get_claim(claim_id, current_user)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    file_size = len(content)
    content_type = file.content_type or "application/octet-stream"

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    document, _ = await document_service.generate_upload_url(
        claim_id=claim_id,
        document_type=document_type,
        filename=file.filename,
        content_type=content_type,
        file_size=file_size,
    )

    try:
        document_service.upload_bytes(
            s3_key=document.s3_key,
            content=content,
            content_type=content_type,
        )
        await document_service.db.commit()
        await document_service.db.refresh(document)
    except DocumentProcessingError as e:
        logger.error(f"Direct upload failed for document {document.id}: {e}")
        await document_service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Direct upload failed for document {document.id}: {e}")
        await document_service.db.rollback()
        raise HTTPException(
            status_code=500, detail="Direct upload to storage failed")

    return {
        "success": True,
        "document_id": str(document.id),
        "filename": document.filename,
        "status": document.status.value,
    }


@router.post(
    "/{document_id}/process",
    response_model=SingleResponse[DocumentResponse],
    summary="Process uploaded document"
)
async def process_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    Trigger processing of an uploaded document.

    Processing includes text extraction, OCR if needed, and embedding generation.
    """
    document = await document_service.get_document(document_id)

    # Verify ownership through parent claim
    await claim_service.get_claim(document.claim_id, current_user)

    # Process immediately to avoid request-scoped session issues in background tasks
    document = await document_service.process_document(document_id)

    return SingleResponse(
        data=DocumentResponse.model_validate(document),
        message="Document processed successfully"
    )


@router.get(
    "/{document_id}",
    response_model=SingleResponse[DocumentResponse],
    summary="Get document details"
)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Get document metadata and status.
    """
    document = await document_service.get_document(document_id)

    return SingleResponse(
        data=DocumentResponse.model_validate(document)
    )


@router.get(
    "/{document_id}/text",
    response_model=DocumentTextResponse,
    summary="Get extracted text"
)
async def get_document_text(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Get extracted text content from a processed document.
    """
    document = await document_service.get_document(document_id)

    return DocumentTextResponse(
        document_id=document.id,
        extracted_text=document.extracted_text,
        status=document.status
    )


@router.get(
    "/{document_id}/download-url",
    response_model=dict,
    summary="Get download URL"
)
async def get_download_url(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Generate a presigned URL for document download.
    """
    url = await document_service.generate_download_url(document_id)

    return {"download_url": url, "expires_in": 43200}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document"
)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Delete a document and its associated data.
    """
    await document_service.delete_document(document_id)
    return None


@router.get(
    "/claim/{claim_id}",
    response_model=List[DocumentResponse],
    summary="List claim documents"
)
async def list_claim_documents(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    List all documents associated with a claim.
    """
    # Verify claim access
    await claim_service.get_claim(claim_id, current_user)

    documents = await document_service.get_claim_documents(claim_id)

    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/user/insurance-policies",
    response_model=List[DocumentResponse],
    summary="List all user's insurance policies"
)
async def list_user_insurance_policies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all insurance policy documents uploaded by the current user across all their claims.
    This allows reusing previously uploaded policies in new claims.
    Returns deduplicated list by filename (keeping the newest version of each file).
    """
    # Get all claims for the user
    claims_result = await db.execute(
        select(Claim.id).where(Claim.user_id == current_user.id)
    )
    claim_ids = [row[0] for row in claims_result.fetchall()]

    if not claim_ids:
        return []

    # Get all insurance policies from user's claims, ordered by created_at desc
    docs_result = await db.execute(
        select(Document).where(
            Document.claim_id.in_(claim_ids),
            Document.document_type == DocumentType.INSURANCE_POLICY
        ).order_by(Document.created_at.desc())
    )
    documents = docs_result.scalars().all()

    # Deduplicate by filename (keep the newest version of each file)
    seen_filenames = set()
    unique_documents = []
    for doc in documents:
        filename_lower = doc.filename.lower()
        if filename_lower not in seen_filenames:
            seen_filenames.add(filename_lower)
            unique_documents.append(doc)

    return [DocumentResponse.model_validate(doc) for doc in unique_documents]


class CopyDocumentRequest(BaseModel):
    """Request body for copying a document to another claim."""
    source_document_id: UUID
    target_claim_id: UUID


@router.post(
    "/copy-to-claim",
    response_model=SingleResponse[DocumentResponse],
    summary="Copy document to another claim"
)
async def copy_document_to_claim(
    request: CopyDocumentRequest,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    claim_service: ClaimService = Depends(get_claim_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Copy an already-processed document to another claim without re-processing.

    This allows reusing previously uploaded and processed documents (like insurance policies)
    in new claims without having to upload and process them again.
    """
    from app.models.embedding import Embedding

    # Get the source document
    source_doc = await document_service.get_document(request.source_document_id)

    # Verify the source document belongs to the user (via claim ownership)
    source_claim_result = await db.execute(
        select(Claim).where(Claim.id == source_doc.claim_id)
    )
    source_claim = source_claim_result.scalar_one_or_none()
    if not source_claim or str(source_claim.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Not authorized to access source document")

    # Verify target claim access
    await claim_service.get_claim(request.target_claim_id, current_user)

    # Check if document is processed (compare as strings for SQLAlchemy compatibility)
    doc_status = source_doc.status.value if hasattr(
        source_doc.status, 'value') else str(source_doc.status)
    if doc_status != DocumentStatus.PROCESSED.value:
        raise HTTPException(
            status_code=400,
            detail="Can only copy processed documents. Please wait for processing to complete."
        )

    # Create new document record with copied data
    new_doc_id = uuid4()
    source_filename = source_doc.filename if isinstance(
        source_doc.filename, str) else str(source_doc.filename)
    source_s3_key = source_doc.s3_key if isinstance(
        source_doc.s3_key, str) else str(source_doc.s3_key)
    new_s3_key = f"documents/{request.target_claim_id}/{new_doc_id}/{source_filename}"

    # Copy the S3 file to new location
    try:
        document_service.copy_s3_object(source_s3_key, new_s3_key)
    except Exception as e:
        logger.error(f"Failed to copy S3 object: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to copy document file")

    # Create new document with the same extracted text and processed status
    new_document = Document(
        id=new_doc_id,
        claim_id=request.target_claim_id,
        document_type=source_doc.document_type,
        filename=source_filename,
        file_size=source_doc.file_size,
        content_type=source_doc.content_type if isinstance(
            source_doc.content_type, str) else str(source_doc.content_type),
        s3_key=new_s3_key,
        status=DocumentStatus.PROCESSED,  # Already processed!
        extracted_text=source_doc.extracted_text
    )

    db.add(new_document)

    # Copy embeddings from source document
    embeddings_result = await db.execute(
        select(Embedding).where(Embedding.document_id == source_doc.id)
    )
    source_embeddings = embeddings_result.scalars().all()

    for src_emb in source_embeddings:
        new_embedding = Embedding(
            id=uuid4(),
            document_id=new_doc_id,
            chunk_index=src_emb.chunk_index,
            chunk_text=src_emb.chunk_text if isinstance(
                src_emb.chunk_text, str) else str(src_emb.chunk_text),
            embedding=src_emb.embedding
        )
        db.add(new_embedding)

    await db.commit()
    await db.refresh(new_document)

    logger.info(
        f"Copied document {source_doc.id} to claim {request.target_claim_id} as {new_doc_id}")

    return SingleResponse(
        data=DocumentResponse.model_validate(new_document),
        message="Document copied successfully"
    )


@router.post(
    "/upload-policy",
    response_model=dict,
    summary="Upload policy document directly"
)
async def upload_policy_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="policy"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Upload a policy document directly for RAG processing.
    This endpoint is for standalone policy documents (not tied to a claim).
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported")

    # Read file content
    content = await file.read()
    file_size = len(content)

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Insurance-only validation from extracted PDF text
    parser = PDFParser()
    extracted_text = await parser.extract_text(content)
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF. Please upload a text-readable insurance policy document."
        )

    if not _looks_like_insurance_policy(extracted_text):
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF does not appear to be an insurance policy. Please upload an insurance policy document only."
        )

    # Reuse or create a dedicated claim for policy chat uploads
    policy_claim_number = f"POLICY-CHAT-{current_user.id}"
    claim_result = await db.execute(
        select(Claim).where(
            Claim.user_id == current_user.id,
            Claim.claim_number == policy_claim_number
        )
    )
    policy_claim = claim_result.scalar_one_or_none()

    if not policy_claim:
        policy_claim = Claim(
            user_id=current_user.id,
            claim_number=policy_claim_number,
            patient_name="Policy Chat Upload",
            status=ClaimStatus.PENDING,
            claim_metadata={"system_generated": True,
                            "purpose": "policy_chat_upload"}
        )
        db.add(policy_claim)
        await db.flush()

    # Create document record
    doc_id = uuid4()
    document = Document(
        id=doc_id,
        claim_id=policy_claim.id,
        document_type=DocumentType.INSURANCE_POLICY,
        filename=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/pdf",
        s3_key=f"policies/{doc_id}/{file.filename}",
        status=DocumentStatus.UPLOADED,
        extracted_text=extracted_text
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    try:
        document_service.upload_bytes(
            s3_key=document.s3_key,
            content=content,
            content_type=document.content_type,
        )
    except DocumentProcessingError as e:
        logger.error(
            f"Failed to upload policy file to storage for document {document.id}: {e}")
        await db.delete(document)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to upload policy file to S3 for document {document.id}: {e}")
        await db.delete(document)
        await db.commit()
        raise HTTPException(
            status_code=500, detail="Failed to store uploaded document")

    return {
        "success": True,
        "data": {
            "id": str(document.id),
            "filename": document.filename,
            "file_size": document.file_size,
            "status": "uploaded"
        }
    }
