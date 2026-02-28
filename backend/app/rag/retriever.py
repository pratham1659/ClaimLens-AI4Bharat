# backend/app/rag/retriever.py
"""
RAG retriever combining embedding search with context building.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import VectorStore
from app.models.embedding import Embedding

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    Retriever for RAG pipeline combining semantic and keyword search.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(db)

    async def retrieve(
        self,
        query: str,
        document_ids: Optional[List[UUID]] = None,
        top_k: int = 10,
        use_hybrid: bool = True,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.

        Args:
            query: Search query
            document_ids: Optional filter by document IDs
            top_k: Number of results to return
            use_hybrid: Whether to use hybrid search
            semantic_weight: Weight for semantic search in hybrid mode

        Returns:
            List of retrieved chunks with metadata
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Perform search
        if use_hybrid:
            results = await self.vector_store.hybrid_search(
                query_embedding=query_embedding,
                keyword_query=query,
                limit=top_k,
                document_ids=document_ids,
                semantic_weight=semantic_weight
            )
        else:
            results = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
                limit=top_k,
                document_ids=document_ids
            )

        # Format results
        retrieved_chunks = []
        for embedding, score in results:
            chunk = {
                "chunk_id": str(embedding.id),
                "document_id": str(embedding.document_id),
                "chunk_index": embedding.chunk_index,
                "content": embedding.chunk_text,
                "relevance_score": float(score),
                "metadata": {}
            }
            retrieved_chunks.append(chunk)

        logger.info(f"Retrieved {len(retrieved_chunks)} chunks for query")
        return retrieved_chunks

    async def retrieve_for_claim(
        self,
        claim_context: Dict[str, Any],
        policy_document_ids: List[UUID],
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Retrieve policy clauses relevant to a claim.

        Args:
            claim_context: Extracted claim information
            policy_document_ids: Policy document IDs to search
            top_k: Number of results

        Returns:
            Relevant policy clauses
        """
        # Build comprehensive query from claim context
        query_parts = []

        # Add diagnoses
        if claim_context.get("diagnoses"):
            for diagnosis in claim_context["diagnoses"]:
                query_parts.append(diagnosis.get("description", ""))

        # Add procedures
        if claim_context.get("procedures"):
            for procedure in claim_context["procedures"]:
                query_parts.append(procedure.get("description", ""))

        # Add medications
        if claim_context.get("medications"):
            for med in claim_context["medications"][:5]:  # Limit medications
                query_parts.append(med.get("name", ""))

        # Combine into query
        query = " ".join(filter(None, query_parts))

        if not query:
            query = "medical insurance coverage benefits exclusions"

        return await self.retrieve(
            query=query,
            document_ids=policy_document_ids,
            top_k=top_k,
            use_hybrid=True
        )

    def build_context(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        max_context_length: int = 8000
    ) -> str:
        """
        Build context string from retrieved chunks.

        Args:
            retrieved_chunks: Retrieved document chunks
            max_context_length: Maximum context length

        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0

        for i, chunk in enumerate(retrieved_chunks):
            chunk_text = f"[Clause {i + 1}] (Relevance: {chunk['relevance_score']:.2f})\n{chunk['content']}\n"

            if current_length + len(chunk_text) > max_context_length:
                break

            context_parts.append(chunk_text)
            current_length += len(chunk_text)

        return "\n---\n".join(context_parts)
