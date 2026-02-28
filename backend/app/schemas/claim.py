# backend/app/schemas/claim.py
"""
Claim-related Pydantic schemas.
"""

from app.schemas.document import DocumentResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.claim import ClaimStatus


class ClaimBase(BaseModel):
    """Base claim schema."""
    patient_name: str = Field(..., min_length=2, max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ClaimCreate(ClaimBase):
    """Schema for claim creation."""
    pass


class ClaimUpdate(BaseModel):
    """Schema for claim updates."""
    patient_name: Optional[str] = Field(None, min_length=2, max_length=255)
    metadata: Optional[Dict[str, Any]] = None


class ClaimResponse(BaseModel):
    """Schema for claim responses."""
    id: UUID
    claim_number: str
    user_id: UUID
    patient_name: str
    status: ClaimStatus
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, alias="claim_metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class ClaimWithDocuments(ClaimResponse):
    """Schema for claim with associated documents."""
    documents: List["DocumentResponse"] = []

    class Config:
        from_attributes = True


class ClaimListResponse(BaseModel):
    """Schema for paginated claim list."""
    claims: List[ClaimResponse]
    total: int
    page: int
    page_size: int


# Import here to avoid circular imports
ClaimWithDocuments.model_rebuild()
