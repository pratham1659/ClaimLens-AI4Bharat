from enum import Enum

from pydantic import BaseModel, Field


class ClaimDecision(str, Enum):
    likely_approved = "likely_approved"
    likely_denied = "likely_denied"
    uncertain = "uncertain"


class Citation(BaseModel):
    clause_id: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    rationale: str


class ClaimAnalyzeRequest(BaseModel):
    discharge_summary_id: str
    policy_id: str
    claim_amount: float | None = None
    notes: str | None = None


class ClaimAnalyzeResponse(BaseModel):
    claim_id: str
    decision: ClaimDecision
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    citations: list[Citation]
    trace_id: str | None = None
