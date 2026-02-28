# backend/app/api/v1/endpoints/claims.py
"""
Claim management endpoints.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.schemas.claim import (
    ClaimCreate,
    ClaimUpdate,
    ClaimResponse,
    ClaimWithDocuments,
    ClaimListResponse
)
from app.schemas.common import SingleResponse
from app.models.claim import ClaimStatus
from app.models.user import User
from app.services.claim_service import ClaimService
from app.api.deps import get_claim_service, get_current_user

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.post(
    "",
    response_model=SingleResponse[ClaimResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create new claim"
)
async def create_claim(
    claim_data: ClaimCreate,
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    Create a new insurance claim.

    - **patient_name**: Name of the patient
    - **metadata**: Optional additional claim metadata
    """
    claim = await claim_service.create_claim(current_user, claim_data)
    return SingleResponse(
        data=ClaimResponse.model_validate(claim),
        message="Claim created successfully"
    )


@router.get(
    "",
    response_model=ClaimListResponse,
    summary="List claims"
)
async def list_claims(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[ClaimStatus] = Query(
        None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    List all claims for the current user with pagination.
    """
    claims, total = await claim_service.list_claims(
        user=current_user,
        page=page,
        page_size=page_size,
        status=status
    )

    return ClaimListResponse(
        claims=[ClaimResponse.model_validate(c) for c in claims],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{claim_id}",
    response_model=SingleResponse[ClaimWithDocuments],
    summary="Get claim details"
)
async def get_claim(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    Get detailed information about a specific claim including documents.
    """
    claim = await claim_service.get_claim(
        claim_id=claim_id,
        user=current_user,
        include_documents=True
    )

    return SingleResponse(
        data=ClaimWithDocuments.model_validate(claim)
    )


@router.patch(
    "/{claim_id}",
    response_model=SingleResponse[ClaimResponse],
    summary="Update claim"
)
async def update_claim(
    claim_id: UUID,
    claim_data: ClaimUpdate,
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    Update claim information.
    """
    claim = await claim_service.update_claim(
        claim_id=claim_id,
        user=current_user,
        claim_data=claim_data
    )

    return SingleResponse(
        data=ClaimResponse.model_validate(claim),
        message="Claim updated successfully"
    )


@router.delete(
    "/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete claim"
)
async def delete_claim(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service)
):
    """
    Delete a claim and all associated documents.
    """
    await claim_service.delete_claim(claim_id, current_user)
    return None
