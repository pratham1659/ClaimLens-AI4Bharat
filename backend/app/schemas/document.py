# backend/app/schemas/document.py
"""
Document-related Pydantic schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.document import DocumentType, DocumentStatus


class DocumentBase(BaseModel):
    """Base document schema."""
    document_type: DocumentType


class DocumentCreate(DocumentBase):
    """Schema for document creation (internal use)."""
    filename: str
    s3_key: str
    file_size: int
    content_type: str


class DocumentResponse(DocumentBase):
    """Schema for document responses."""
    id: UUID
    claim_id: UUID
    filename: str
    file_size: int
    content_type: str
    status: DocumentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    document_id: UUID
    upload_url: str
    expires_in: int


class DocumentTextResponse(BaseModel):
    """Schema for extracted document text."""
    document_id: UUID
    extracted_text: Optional[str]
    status: DocumentStatus
