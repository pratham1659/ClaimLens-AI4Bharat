# backend/app/services/claim_service.py
"""
Claim service for claim management operations.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.claim import Claim, ClaimStatus
from app.models.document import Document
from app.models.user import User
from app.schemas.claim import ClaimCreate, ClaimUpdate
from app.core.exceptions import ResourceNotFoundError, AuthorizationError
from app.auth.permissions import check_resource_ownership

logger = logging.getLogger(__name__)


class ClaimService:
    """
    Service for claim-related operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_claim(
        self,
        user: User,
        claim_data: ClaimCreate
    ) -> Claim:
        """
        Create a new claim.

        Args:
            user: Creating user
            claim_data: Claim data

        Returns:
            Created claim
        """
        # Generate unique claim number
        claim_number = self._generate_claim_number()

        claim = Claim(
            user_id=user.id,
            claim_number=claim_number,
            patient_name=claim_data.patient_name,
            status=ClaimStatus.PENDING,
            metadata=claim_data.metadata or {}
        )

        self.db.add(claim)
        await self.db.flush()

        logger.info(f"Created claim: {claim_number} by user {user.email}")
        return claim

    async def get_claim(
        self,
        claim_id: UUID,
        user: User,
        include_documents: bool = False
    ) -> Claim:
        """
        Get claim by ID with authorization check.

        Args:
            claim_id: Claim ID
            user: Requesting user
            include_documents: Whether to include documents

        Returns:
            Claim

        Raises:
            ResourceNotFoundError: If claim not found
            AuthorizationError: If user not authorized
        """
        query = select(Claim).where(Claim.id == claim_id)

        if include_documents:
            query = query.options(selectinload(Claim.documents))

        result = await self.db.execute(query)
        claim = result.scalar_one_or_none()

        if not claim:
            raise ResourceNotFoundError("Claim", claim_id)

        if not check_resource_ownership(user, str(claim.user_id)):
            raise AuthorizationError("Not authorized to access this claim")

        return claim

    async def list_claims(
        self,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ClaimStatus] = None
    ) -> Tuple[List[Claim], int]:
        """
        List claims for a user with pagination.

        Args:
            user: User
            page: Page number
            page_size: Items per page
            status: Optional status filter

        Returns:
            Tuple of (claims, total_count)
        """
        query = select(Claim).where(Claim.user_id == user.id)

        if status:
            query = query.where(Claim.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        # Apply pagination
        query = query.order_by(Claim.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        claims = result.scalars().all()

        return list(claims), total

    async def update_claim(
        self,
        claim_id: UUID,
        user: User,
        claim_data: ClaimUpdate
    ) -> Claim:
        """
        Update a claim.

        Args:
            claim_id: Claim ID
            user: Requesting user
            claim_data: Update data

        Returns:
            Updated claim
        """
        claim = await self.get_claim(claim_id, user)

        update_data = claim_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(claim, field, value)

        await self.db.flush()
        logger.info(f"Updated claim: {claim.claim_number}")

        return claim

    async def update_status(
        self,
        claim_id: UUID,
        status: ClaimStatus
    ) -> Claim:
        """
        Update claim status (internal use).

        Args:
            claim_id: Claim ID
            status: New status

        Returns:
            Updated claim
        """
        result = await self.db.execute(
            select(Claim).where(Claim.id == claim_id)
        )
        claim = result.scalar_one_or_none()

        if not claim:
            raise ResourceNotFoundError("Claim", claim_id)

        claim.status = status
        await self.db.flush()

        logger.info(
            f"Updated claim {claim.claim_number} status to {status.value}")
        return claim

    async def delete_claim(
        self,
        claim_id: UUID,
        user: User
    ) -> None:
        """
        Delete a claim and associated documents.

        Args:
            claim_id: Claim ID
            user: Requesting user
        """
        claim = await self.get_claim(claim_id, user, include_documents=True)

        await self.db.delete(claim)
        await self.db.flush()

        logger.info(f"Deleted claim: {claim.claim_number}")

    def _generate_claim_number(self) -> str:
        """Generate unique claim number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid4())[:8].upper()
        return f"CLM-{timestamp}-{unique_id}"
