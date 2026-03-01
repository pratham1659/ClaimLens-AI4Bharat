# backend/app/schemas/analysis.py
"""
Analysis-related Pydantic schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, AliasChoices
from uuid import UUID
from datetime import datetime
from app.models.analysis import ApprovalLikelihood


class ComplianceRisk(BaseModel):
    """Schema for individual compliance risk."""
    risk_id: str
    severity: str = Field(..., pattern="^(high|medium|low)$")
    description: str
    affected_clause: Optional[str] = None


class ClauseReference(BaseModel):
    """Schema for policy clause reference."""
    clause_id: str
    clause_text: str
    relevance_score: float = Field(..., ge=0, le=1)
    source_document: str


class Recommendation(BaseModel):
    """Schema for corrective recommendation."""
    recommendation_id: str
    priority: str = Field(..., pattern="^(high|medium|low)$")
    action: str
    rationale: str


class AnalysisRequest(BaseModel):
    """Schema for analysis request."""
    claim_id: UUID = Field(validation_alias=AliasChoices("claim_id", "claimId"))


class AnalysisResponse(BaseModel):
    """Schema for analysis results."""
    id: UUID
    claim_id: UUID
    approval_score: float = Field(..., ge=0, le=100)
    approval_likelihood: ApprovalLikelihood
    compliance_risks: List[ComplianceRisk]
    clause_references: List[ClauseReference]
    missing_documentation: List[str]
    recommendations: List[Recommendation]
    reasoning: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisSummary(BaseModel):
    """Schema for analysis summary in claim list."""
    approval_score: float
    approval_likelihood: ApprovalLikelihood
    risk_count: int
    created_at: datetime
