# backend/app/core/exceptions.py
"""
Custom exception classes and global exception handlers.
Provides consistent error responses across the application.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ClaimLensException(Exception):
    """Base exception for ClaimLens application."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(ClaimLensException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(ClaimLensException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ResourceNotFoundError(ClaimLensException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} with ID {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "id": str(resource_id)}
        )


class ValidationError(ClaimLensException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class DocumentProcessingError(ClaimLensException):
    """Raised when document processing fails."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="DOCUMENT_PROCESSING_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AIServiceError(ClaimLensException):
    """Raised when AI service (Bedrock) fails."""

    def __init__(self, message: str = "AI service unavailable", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class RateLimitExceededError(ClaimLensException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after}
        )


async def claimlens_exception_handler(
    request: Request,
    exc: ClaimLensException
) -> JSONResponse:
    """
    Global exception handler for ClaimLens exceptions.
    """
    logger.error(
        f"ClaimLens Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details
        ).model_dump()
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handler for Pydantic validation errors.
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors}
        ).model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    Handler for FastAPI HTTP exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code="HTTP_ERROR",
            message=exc.detail,
            details=None
        ).model_dump()
    )
