# backend/app/rag/retriever.py
"""
RAG retriever combining embedding search with context building.
Supports both local (FAISS + HuggingFace) and production (pgvector + Bedrock) modes.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.vector_store import VectorStore
from app.models.embedding import Embedding

logger = logging.getLogger(__name__)


class SimpleFAISSRetriever:
    """
    Simple wrapper around FAISS vectorstore for direct retrieval.
    Avoids the BM25 requirement of ClaimLensRetriever.
    """

    def __init__(self, vectorstore, top_k: int = 20):
        self.vectorstore = vectorstore
        self.top_k = top_k

    def retrieve(self, query: str, return_stages: bool = False):
        """
        Retrieve documents from FAISS index.

        Args:
            query: Search query
            return_stages: Whether to return intermediate stages (ignored)

        Returns:
            List of langchain Document objects
        """
        results = self.vectorstore.similarity_search(query, k=self.top_k)
        return results


class RAGRetriever:
    """
    Retriever for RAG pipeline combining semantic and keyword search.
    Automatically switches between local and production modes.
    """

    def __init__(self, db: AsyncSession, force_mode: Optional[str] = None):
        """
        Initialize RAG retriever.

        Args:
            db: Database session
            force_mode: Force a specific embedding mode ('local', 'bedrock', 'mock')
        """
        self.db = db
        self.embedding_service = get_embedding_service(force_mode=force_mode)
        self.vector_store = VectorStore(db)
        self._local_retriever = None

        # Detect mode
        self.use_local_faiss = self._should_use_local_faiss()

        logger.info(f"RAGRetriever initialized - embedding mode: {self.embedding_service.mode}, "
                    f"use_local_faiss: {self.use_local_faiss}")

    def _should_use_local_faiss(self) -> bool:
        """Determine if we should use local FAISS index."""
        use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
        bedrock_enabled = os.getenv(
            "BEDROCK_ENABLED", "true").lower() == "true"
        environment = os.getenv("ENVIRONMENT", "development").lower()

        return use_mock or not bedrock_enabled or environment == "development"

    def _get_local_retriever(self):
        """Lazy load the local FAISS-based retriever."""
        if self._local_retriever is None and self.use_local_faiss:
            try:
                from app.retriever.embeddings import load_embedding_model
                from langchain_core.documents import Document as LangchainDoc
                from langchain_community.vectorstores import FAISS
                import json

                # Load FAISS index if available
                index_path = os.getenv(
                    "FAISS_INDEX_PATH", "faiss_claimlens_index")
                combined_index_path = os.getenv(
                    "FAISS_COMBINED_INDEX_PATH", "faiss_claimlens_combined_index")

                # Check for combined index first, then regular
                if os.path.exists(combined_index_path):
                    actual_path = combined_index_path
                elif os.path.exists(index_path):
                    actual_path = index_path
                else:
                    logger.warning(
                        f"No FAISS index found at {index_path} or {combined_index_path}")
                    return None

                model_size = os.getenv("EMBEDDING_MODEL_SIZE", "base")
                embedding_model = load_embedding_model(model_size=model_size)

                # Load FAISS vectorstore directly instead of using ClaimLensRetriever
                # This avoids the BM25 requirement
                logger.info(f"Loading FAISS index from: {actual_path}")
                vectorstore = FAISS.load_local(
                    actual_path,
                    embedding_model,
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS index loaded successfully.")

                # Create a simple retriever wrapper
                self._local_retriever = SimpleFAISSRetriever(
                    vectorstore=vectorstore,
                    top_k=20
                )
                logger.info(f"Local FAISS retriever loaded from {actual_path}")

            except Exception as e:
                logger.error(f"Failed to initialize local retriever: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self._local_retriever = None

        return self._local_retriever

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
        # Try local FAISS retriever first if available and no document filter
        if self.use_local_faiss and document_ids is None:
            local_results = await self._retrieve_local(query, top_k)
            if local_results:
                return local_results

        # Fall back to pgvector-based search
        return await self._retrieve_pgvector(
            query=query,
            document_ids=document_ids,
            top_k=top_k,
            use_hybrid=use_hybrid,
            semantic_weight=semantic_weight
        )

    async def _retrieve_local(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using local FAISS index.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of retrieved chunks
        """
        retriever = self._get_local_retriever()
        if retriever is None:
            return []

        try:
            results = retriever.retrieve(query, return_stages=False)

            # Format results
            retrieved_chunks = []
            for i, doc in enumerate(results[:top_k]):
                chunk = {
                    "chunk_id": doc.metadata.get("clause_id", f"local_{i}"),
                    "document_id": doc.metadata.get("document_id", ""),
                    "chunk_index": doc.metadata.get("chunk_index", i),
                    "content": doc.page_content,
                    # Decreasing relevance
                    "relevance_score": 1.0 - (i * 0.05),
                    "metadata": doc.metadata,
                    "source": "local_faiss"
                }
                retrieved_chunks.append(chunk)

            logger.info(
                f"Local retrieval returned {len(retrieved_chunks)} chunks")
            return retrieved_chunks

        except Exception as e:
            logger.error(f"Local retrieval failed: {e}")
            return []

    async def _retrieve_pgvector(
        self,
        query: str,
        document_ids: Optional[List[UUID]] = None,
        top_k: int = 10,
        use_hybrid: bool = True,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using pgvector database.

        Args:
            query: Search query
            document_ids: Optional filter by document IDs
            top_k: Number of results
            use_hybrid: Whether to use hybrid search
            semantic_weight: Weight for semantic search

        Returns:
            List of retrieved chunks
        """
        try:
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
                    "metadata": {},
                    "source": "pgvector"
                }
                retrieved_chunks.append(chunk)

            logger.info(
                f"pgvector retrieval returned {len(retrieved_chunks)} chunks")
            return retrieved_chunks

        except Exception as e:
            logger.error(f"pgvector retrieval failed: {e}")
            return []

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


# Convenience function for creating retriever
def create_rag_retriever(db: AsyncSession, force_mode: Optional[str] = None) -> RAGRetriever:
    """
    Create a RAG retriever instance.

    Args:
        db: Database session
        force_mode: Force a specific mode ('local', 'bedrock', 'mock')

    Returns:
        RAGRetriever instance
    """
    return RAGRetriever(db, force_mode=force_mode)
