# backend/app/auth/jwt_handler.py
"""
JWT token handling and validation.
"""

from typing import Optional
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_token
from app.core.exceptions import AuthenticationError
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.

    Args:
        credentials: Bearer token from request header
        db: Database session

    Returns:
        Authenticated user object

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = credentials.credentials

    payload = decode_token(token)
    if payload is None:
        raise AuthenticationError("Invalid or expired token")

    # Check token type
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")

    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active.
    """
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get current user.
    Returns None if no valid token provided.
    """
    if credentials is None:
        return None

    try:
        return get_current_user(credentials, db)
    except AuthenticationError:
        return None
