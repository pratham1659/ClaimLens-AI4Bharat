# backend/app/models/claim.py
"""
Claim model for insurance claim submissions.
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base


class ClaimStatus(str, enum.Enum):
    """Claim processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class Claim(Base):
    """
    Claim model representing insurance claim submissions.

    Attributes:
        id: Unique identifier
        user_id: Reference to submitting user
        claim_number: External claim reference number
        patient_name: Name of the patient
        status: Current processing status
        metadata: Additional claim metadata
    """

    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id"), nullable=False)
    claim_number = Column(String(100), unique=True, index=True, nullable=False)
    patient_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(ClaimStatus),
                    default=ClaimStatus.PENDING, nullable=False)
    claim_metadata = Column(JSON, default=dict)

    # Relationships
    user = relationship("User", back_populates="claims")
    documents = relationship(
        "Document", back_populates="claim", cascade="all, delete-orphan")
    analysis_results = relationship(
        "AnalysisResult", back_populates="claim", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Claim {self.claim_number}>"
