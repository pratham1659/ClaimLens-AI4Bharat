# backend/app/api/v1/endpoints/documents.py
"""
Document management endpoints.
"""

from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, status, BackgroundTasks, UploadFile, File, Form

from app.schemas.document import (
    DocumentResponse,
    DocumentUploadResponse,
    DocumentTextResponse
)
from app.schemas.common import SingleResponse
from app.models.document import DocumentType, Document, DocumentStatus
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
from pydantic import BaseModel


router = APIRouter(prefix="/documents", tags=["Documents"])


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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Trigger processing of an uploaded document.

    Processing includes text extraction, OCR if needed, and embedding generation.
    """
    document = await document_service.get_document(document_id)

    # Process in background for large files
    background_tasks.add_task(
        document_service.process_document,
        document_id
    )

    return SingleResponse(
        data=DocumentResponse.model_validate(document),
        message="Document processing started"
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
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a policy document directly for RAG processing.
    This endpoint is for standalone policy documents (not tied to a claim).
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return {"success": False, "error": "Only PDF files are supported"}

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Create document record
    doc_id = uuid4()
    document = Document(
        id=doc_id,
        claim_id=None,  # Standalone policy document
        document_type=DocumentType.INSURANCE_POLICY,
        filename=file.filename,
        original_filename=file.filename,
        file_size=file_size,
        mime_type=file.content_type or "application/pdf",
        s3_key=f"policies/{doc_id}/{file.filename}",
        status=DocumentStatus.UPLOADED
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return {
        "success": True,
        "data": {
            "id": str(document.id),
            "filename": document.filename,
            "file_size": document.file_size,
            "status": "uploaded"
        }
    }
