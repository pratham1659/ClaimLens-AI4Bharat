# backend/app/core/security.py
"""
Security utilities for password hashing and verification.
Uses bcrypt for secure password storage.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.core.config import settings


# Password hashing context using bcrypt
# truncate_error=False allows handling of passwords > 72 bytes
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def _truncate_password(password: str, max_length: int = 72) -> str:
    """
    Truncate password to max_length bytes for bcrypt compatibility.
    Bcrypt has a maximum password length of 72 bytes.

    Args:
        password: Plain text password
        max_length: Maximum byte length (default 72 for bcrypt)

    Returns:
        Truncated password string
    """
    # Encode to bytes to handle UTF-8 properly
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > max_length:
        # Truncate to max_length bytes and decode back
        password_bytes = password_bytes[:max_length]
        # Ensure we don't break in the middle of a UTF-8 character
        try:
            return password_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # If truncation broke a UTF-8 char, remove bytes until valid
            while password_bytes:
                password_bytes = password_bytes[:-1]
                try:
                    return password_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    continue
            return ""
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.

    Args:
        plain_password: The password to verify
        hashed_password: The stored password hash

    Returns:
        True if password matches, False otherwise
    """
    # Truncate password to 72 bytes for bcrypt compatibility
    truncated_password = _truncate_password(plain_password)
    return pwd_context.verify(truncated_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a secure hash for a password.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash of the password
    """
    # Truncate password to 72 bytes for bcrypt compatibility
    truncated_password = _truncate_password(password)
    return pwd_context.hash(truncated_password)


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The token subject (usually user ID)
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional JWT claims

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_refresh_token(subject: Union[str, int]) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        subject: The token subject (usually user ID)

    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
