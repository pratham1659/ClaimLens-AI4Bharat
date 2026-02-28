# backend/app/models/user.py
"""
User model for authentication and authorization.
"""

from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.models.base import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    """
    User model representing application users.

    Attributes:
        id: Unique identifier
        email: User email (unique)
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        role: User role for access control
        is_active: Whether user account is active
        is_verified: Whether email is verified
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.ANALYST, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    claims = relationship("Claim", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
