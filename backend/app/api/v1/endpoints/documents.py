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

    matches = sum(1 for token in INSURANCE_POLICY_KEYWORDS if token in normalized)
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
        expires_in=3600
    )


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

    return {"download_url": url, "expires_in": 3600}


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
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

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
            claim_metadata={"system_generated": True, "purpose": "policy_chat_upload"}
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
        document_service.s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=document.s3_key,
            Body=content,
            ContentType=document.content_type,
        )
    except Exception as e:
        logger.error(f"Failed to upload policy file to S3 for document {document.id}: {e}")
        await db.delete(document)
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to store uploaded document")

    return {
        "success": True,
        "data": {
            "id": str(document.id),
            "filename": document.filename,
            "file_size": document.file_size,
            "status": "uploaded"
        }
    }
