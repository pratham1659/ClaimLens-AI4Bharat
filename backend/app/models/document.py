# backend/app/models/document.py
"""
Document model for uploaded files.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base


class DocumentType(str, enum.Enum):
    """Types of documents that can be uploaded."""
    DISCHARGE_SUMMARY = "discharge_summary"
    INSURANCE_POLICY = "insurance_policy"
    BILLING_DATA = "billing_data"


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(Base):
    """
    Document model for uploaded files.

    Attributes:
        id: Unique identifier
        claim_id: Reference to parent claim
        document_type: Type of document
        filename: Original filename
        s3_key: S3 object key
        file_size: File size in bytes
        content_type: MIME type
        status: Processing status
        extracted_text: Text extracted from document
    """

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey(
        "claims.id"), nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    status = Column(SQLEnum(DocumentStatus),
                    default=DocumentStatus.UPLOADED, nullable=False)
    extracted_text = Column(Text, nullable=True)

    # Relationships
    claim = relationship("Claim", back_populates="documents")
    embeddings = relationship(
        "Embedding", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document {self.filename}>"
