# backend/app/api/deps.py
"""
API dependencies for dependency injection.
"""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.auth.jwt_handler import get_current_user, get_current_active_user
from app.models.user import User
from app.services.user_service import UserService
from app.services.claim_service import ClaimService
from app.services.document_service import DocumentService
from app.services.analysis_service import AnalysisService


async def get_user_service(
    db: AsyncSession = Depends(get_db)
) -> UserService:
    """Get user service instance."""
    return UserService(db)


async def get_claim_service(
    db: AsyncSession = Depends(get_db)
) -> ClaimService:
    """Get claim service instance."""
    return ClaimService(db)


async def get_document_service(
    db: AsyncSession = Depends(get_db)
) -> DocumentService:
    """Get document service instance."""
    return DocumentService(db)


async def get_analysis_service(
    db: AsyncSession = Depends(get_db)
) -> AnalysisService:
    """Get analysis service instance."""
    return AnalysisService(db)
