# backend/app/rag/vector_store.py
"""
Vector store operations using PostgreSQL with pgvector.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
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
        self.target_embedding_dimension = 1536

    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding vector length to match pgvector column dimension."""
        current_dim = len(embedding)

        if current_dim == self.target_embedding_dimension:
            return embedding

        if current_dim > self.target_embedding_dimension:
            logger.warning(
                f"Truncating embedding dimension from {current_dim} to {self.target_embedding_dimension}"
            )
            return embedding[:self.target_embedding_dimension]

        logger.warning(
            f"Padding embedding dimension from {current_dim} to {self.target_embedding_dimension}"
        )
        return embedding + [0.0] * (self.target_embedding_dimension - current_dim)

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
            normalized_embedding = self._normalize_embedding(embedding)
            record = Embedding(
                document_id=document_id,
                chunk_index=i,
                chunk_text=chunk,
                embedding=normalized_embedding
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
        threshold: Optional[float] = None
    ) -> List[Tuple[Embedding, float]]:
        """
        Perform similarity search.

        Args:
            query_embedding: Query vector
            limit: Maximum results
            document_ids: Optional filter by document IDs
            threshold: Optional minimum similarity threshold

        Returns:
            List of (embedding, similarity_score) tuples
        """
        # Build query with cosine similarity
        normalized_query_embedding = self._normalize_embedding(query_embedding)
        query = select(
            Embedding,
            (1 - Embedding.embedding.cosine_distance(normalized_query_embedding)).label("similarity")
        )

        # Filter by document IDs if provided
        if document_ids:
            query = query.where(Embedding.document_id.in_(document_ids))

        # Optionally filter by threshold, then order by nearest neighbor distance
        if threshold is not None:
            query = query.where(
                (1 - Embedding.embedding.cosine_distance(normalized_query_embedding)) >= threshold
            )

        query = query.order_by(
            Embedding.embedding.cosine_distance(normalized_query_embedding)
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
        normalized_query_embedding = self._normalize_embedding(query_embedding)
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
                "query_embedding": normalized_query_embedding,
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

    async def keyword_search(
        self,
        keyword_query: str,
        limit: int = 10,
        document_ids: Optional[List[UUID]] = None,
    ) -> List[Tuple[Embedding, float]]:
        """Perform keyword-only fallback search when semantic embedding generation is unavailable."""
        query = text("""
            SELECT
                e.id,
                e.document_id,
                e.chunk_text,
                e.chunk_index,
                e.embedding,
                COALESCE(
                    ts_rank(
                        to_tsvector('english', e.chunk_text),
                        websearch_to_tsquery('english', :keyword_query)
                    ),
                    0
                ) AS keyword_score
            FROM embeddings e
            WHERE (:doc_filter = false OR e.document_id = ANY(:document_ids))
              AND (
                    to_tsvector('english', e.chunk_text) @@ websearch_to_tsquery('english', :keyword_query)
                    OR e.chunk_text ILIKE :ilike_pattern
                  )
            ORDER BY keyword_score DESC, e.chunk_index ASC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "keyword_query": keyword_query,
                "document_ids": document_ids or [],
                "doc_filter": document_ids is not None,
                "ilike_pattern": f"%{keyword_query}%",
                "limit": limit,
            },
        )

        rows = result.fetchall()
        embeddings_with_scores: List[Tuple[Embedding, float]] = []
        for row in rows:
            embedding = Embedding(
                id=row.id,
                document_id=row.document_id,
                chunk_text=row.chunk_text,
                chunk_index=row.chunk_index,
                embedding=row.embedding,
            )
            embeddings_with_scores.append((embedding, float(row.keyword_score or 0.0)))

        return embeddings_with_scores

    async def debug_nearest_neighbors(
        self,
        query_embedding: List[float],
        limit: int = 5,
        document_ids: Optional[List[UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """Return raw nearest-neighbor diagnostics for troubleshooting retrieval quality."""
        normalized_query_embedding = self._normalize_embedding(query_embedding)
        distance_expr = Embedding.embedding.cosine_distance(normalized_query_embedding)
        query = select(
            Embedding,
            distance_expr.label("distance"),
            (1 - distance_expr).label("similarity"),
        )

        if document_ids:
            query = query.where(Embedding.document_id.in_(document_ids))

        query = query.order_by(distance_expr).limit(limit)
        result = await self.db.execute(query)

        rows = result.all()
        diagnostics: List[Dict[str, Any]] = []
        for row in rows:
            emb = row.Embedding
            diagnostics.append(
                {
                    "chunk_id": str(emb.id),
                    "document_id": str(emb.document_id),
                    "chunk_index": emb.chunk_index,
                    "distance": float(row.distance),
                    "similarity": float(row.similarity),
                    "chunk_preview": (emb.chunk_text or "")[:200],
                }
            )

        return diagnostics

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
