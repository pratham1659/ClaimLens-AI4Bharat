# backend/app/schemas/common.py
"""
Common schema definitions used across the application.
"""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar("T")


class ResponseBase(BaseModel):
    """Base response schema."""
    success: bool = True
    message: Optional[str] = None


class PaginatedResponse(ResponseBase, Generic[T]):
    """Paginated response schema."""
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class SingleResponse(ResponseBase, Generic[T]):
    """Single item response schema."""
    data: T


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime
