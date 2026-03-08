# backend/app/schemas/user.py
"""
User-related Pydantic schemas.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=100)

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    """Schema for user responses."""
    id: UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


class ResetPasswordRequest(BaseModel):
    """Schema for password reset with old password verification."""
    email: EmailStr
    old_password: str
    new_password: str = Field(..., min_length=4, max_length=100)
