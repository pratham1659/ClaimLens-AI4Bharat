# backend/app/services/user_service.py
"""
User service for authentication and user management.
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import ValidationError, ResourceNotFoundError, AuthenticationError

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user-related operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User registration data

        Returns:
            Created user

        Raises:
            ValidationError: If email already exists
        """
        # Check if email exists
        existing = await self.get_by_email(user_data.email)
        if existing:
            raise ValidationError(
                "Email already registered",
                details={"email": user_data.email}
            )

        # Create user
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            role=UserRole.ANALYST,
            is_active=True,
            is_verified=False
        )

        self.db.add(user)

        try:
            await self.db.flush()
            logger.info(f"Created user: {user.email}")
            return user
        except IntegrityError:
            await self.db.rollback()
            raise ValidationError("Failed to create user")

    async def authenticate(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            Authenticated user

        Raises:
            AuthenticationError: If credentials are invalid
        """
        user = await self.get_by_email(email)

        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("User account is deactivated")

        logger.info(f"User authenticated: {email}")
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate
    ) -> User:
        """
        Update user profile.

        Args:
            user_id: User ID
            user_data: Update data

        Returns:
            Updated user
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", user_id)

        update_data = user_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        logger.info(f"Updated user: {user.email}")

        return user

    async def deactivate_user(self, user_id: UUID) -> User:
        """Deactivate a user account."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", user_id)

        user.is_active = False
        await self.db.flush()

        logger.info(f"Deactivated user: {user.email}")
        return user

    async def reset_password_with_old(
        self, email: str, old_password: str, new_password: str
    ) -> bool:
        """
        Reset password by verifying old password.

        Args:
            email: User email
            old_password: Current password
            new_password: New password

        Returns:
            True if password was reset successfully
        """
        user = await self.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(old_password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()

        logger.info(f"Password reset completed for user: {user.email}")
        return True
