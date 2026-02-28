# backend/app/api/v1/endpoints/auth.py
"""
Authentication endpoints.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    TokenResponse,
    TokenRefresh
)
from app.schemas.common import SingleResponse
from app.services.user_service import UserService
from app.api.deps import get_user_service, get_current_user
from app.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings
from app.core.exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=SingleResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, mixed case, numbers)
    - **full_name**: User's full name
    """
    user = await user_service.create_user(user_data)
    return SingleResponse(
        data=UserResponse.model_validate(user),
        message="User registered successfully"
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login"
)
async def login(
    credentials: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticate user and return access tokens.

    - **email**: Registered email address
    - **password**: User password
    """
    user = await user_service.authenticate(
        email=credentials.email,
        password=credentials.password
    )

    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={"role": user.role.value}
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token"
)
async def refresh_token(
    token_data: TokenRefresh,
    user_service: UserService = Depends(get_user_service)
):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(token_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")

    user_id = payload.get("sub")
    user = await user_service.get_by_id(user_id)

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={"role": user.role.value}
    )
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get(
    "/me",
    response_model=SingleResponse[UserResponse],
    summary="Get current user"
)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's profile.
    """
    return SingleResponse(
        data=UserResponse.model_validate(current_user)
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout"
)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user (client should discard tokens).
    """
    # In a production system, you might want to blacklist the token
    # For now, we just return success and let client discard tokens
    return None
