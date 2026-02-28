# backend/app/models/base.py
"""
Base model class with common fields and utilities.
"""

from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Base(DeclarativeBase):
    """
    Base class for all database models.
    Provides common fields and utilities.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"

    # Common timestamp fields
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
