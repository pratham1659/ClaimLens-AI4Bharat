# backend/app/rag/vector_store.py
"""
Vector store operations using PostgreSQL with pgvector.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector

from app.models.embedding import Embedding
from app.models.document import Document

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector store for semantic search using pgvector.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def store_embeddings(
        self,
        document_id: UUID,
        chunks: List[str],
        embeddings: List[List[float]]
    ) -> List[Embedding]:
        """
        Store document chunk embeddings.

        Args:
            document_id: Source document ID
            chunks: Text chunks
            embeddings: Corresponding embeddings

        Returns:
            List of created embedding records
        """
        embedding_records = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            record = Embedding(
                document_id=document_id,
                chunk_index=i,
                chunk_text=chunk,
                embedding=embedding
            )
            self.db.add(record)
            embedding_records.append(record)

        await self.db.flush()
        logger.info(
            f"Stored {len(embedding_records)} embeddings for document {document_id}")

        return embedding_records

    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        document_ids: Optional[List[UUID]] = None,
        threshold: float = 0.7
    ) -> List[Tuple[Embedding, float]]:
        """
        Perform similarity search.

        Args:
            query_embedding: Query vector
            limit: Maximum results
            document_ids: Optional filter by document IDs
            threshold: Minimum similarity threshold

        Returns:
            List of (embedding, similarity_score) tuples
        """
        # Build query with cosine similarity
        query = select(
            Embedding,
            (1 - Embedding.embedding.cosine_distance(query_embedding)).label("similarity")
        )

        # Filter by document IDs if provided
        if document_ids:
            query = query.where(Embedding.document_id.in_(document_ids))

        # Filter by threshold and order by similarity
        query = query.where(
            (1 - Embedding.embedding.cosine_distance(query_embedding)) >= threshold
        ).order_by(
            Embedding.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        return [(row.Embedding, row.similarity) for row in rows]

    async def hybrid_search(
        self,
        query_embedding: List[float],
        keyword_query: str,
        limit: int = 10,
        document_ids: Optional[List[UUID]] = None,
        semantic_weight: float = 0.7
    ) -> List[Tuple[Embedding, float]]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query_embedding: Query vector for semantic search
            keyword_query: Keywords for text search
            limit: Maximum results
            document_ids: Optional filter by document IDs
            semantic_weight: Weight for semantic vs keyword (0-1)

        Returns:
            List of (embedding, combined_score) tuples
        """
        keyword_weight = 1 - semantic_weight

        # Build hybrid query
        query = text("""
            WITH semantic_results AS (
                SELECT 
                    id,
                    document_id,
                    chunk_text,
                    chunk_index,
                    embedding,
                    1 - (embedding <=> :query_embedding) as semantic_score
                FROM embeddings
                WHERE (:doc_filter = false OR document_id = ANY(:document_ids))
            ),
            keyword_results AS (
                SELECT 
                    id,
                    ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', :keyword_query)) as keyword_score
                FROM embeddings
                WHERE to_tsvector('english', chunk_text) @@ plainto_tsquery('english', :keyword_query)
            )
            SELECT 
                s.id,
                s.document_id,
                s.chunk_text,
                s.chunk_index,
                s.embedding,
                (s.semantic_score * :semantic_weight + COALESCE(k.keyword_score, 0) * :keyword_weight) as combined_score
            FROM semantic_results s
            LEFT JOIN keyword_results k ON s.id = k.id
            ORDER BY combined_score DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "query_embedding": query_embedding,
                "keyword_query": keyword_query,
                "document_ids": document_ids or [],
                "doc_filter": document_ids is not None,
                "semantic_weight": semantic_weight,
                "keyword_weight": keyword_weight,
                "limit": limit
            }
        )

        rows = result.fetchall()

        # Convert to Embedding objects
        embeddings_with_scores = []
        for row in rows:
            embedding = Embedding(
                id=row.id,
                document_id=row.document_id,
                chunk_text=row.chunk_text,
                chunk_index=row.chunk_index,
                embedding=row.embedding
            )
            embeddings_with_scores.append((embedding, row.combined_score))

        return embeddings_with_scores

    async def delete_document_embeddings(self, document_id: UUID) -> int:
        """
        Delete all embeddings for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted embeddings
        """
        result = await self.db.execute(
            select(Embedding).where(Embedding.document_id == document_id)
        )
        embeddings = result.scalars().all()

        for embedding in embeddings:
            await self.db.delete(embedding)

        return len(embeddings)
