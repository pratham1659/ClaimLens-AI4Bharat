# backend/app/models/analysis.py
"""
Analysis result model for storing AI compliance analysis.
"""

from sqlalchemy import Column, String, Float, ForeignKey, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base


class ApprovalLikelihood(str, enum.Enum):
    """Approval likelihood categories."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class AnalysisResult(Base):
    """
    Analysis result model for storing AI compliance analysis.

    Attributes:
        id: Unique identifier
        claim_id: Reference to analyzed claim
        approval_score: Numerical approval likelihood (0-100)
        approval_likelihood: Categorical likelihood
        compliance_risks: List of identified risks
        clause_references: Referenced policy clauses
        missing_documentation: List of missing documents
        recommendations: Corrective recommendations
        reasoning: AI reasoning explanation
        raw_response: Raw LLM response for debugging
    """

    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey(
        "claims.id"), nullable=False)
    approval_score = Column(Float, nullable=False)
    approval_likelihood = Column(SQLEnum(ApprovalLikelihood), nullable=False)
    compliance_risks = Column(JSON, default=list)
    clause_references = Column(JSON, default=list)
    missing_documentation = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    reasoning = Column(Text, nullable=False)
    raw_response = Column(JSON, nullable=True)

    # Relationships
    claim = relationship("Claim", back_populates="analysis_results")

    def __repr__(self) -> str:
        return f"<AnalysisResult claim={self.claim_id} score={self.approval_score}>"
