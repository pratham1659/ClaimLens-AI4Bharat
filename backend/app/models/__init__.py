# backend/app/models/__init__.py
"""
SQLAlchemy models for ClaimLens AI database.
"""

from app.models.user import User
from app.models.claim import Claim
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.analysis import AnalysisResult

__all__ = ["User", "Claim", "Document", "Embedding", "AnalysisResult"]
