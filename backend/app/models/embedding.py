# backend/app/models/embedding.py
"""
Embedding model for vector storage with pgvector.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base


class Embedding(Base):
    """
    Embedding model for storing document chunk vectors.
    Uses pgvector for efficient similarity search.

    Attributes:
        id: Unique identifier
        document_id: Reference to source document
        chunk_index: Position of chunk in document
        chunk_text: Original text of the chunk
        embedding: Vector embedding (1536 dimensions for Titan)
        metadata: Additional metadata about the chunk
    """

    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey(
        "documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    # Titan embedding dimension
    embedding = Column(Vector(1536), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding doc={self.document_id} chunk={self.chunk_index}>"
