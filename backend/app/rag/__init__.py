# backend/app/rag/__init__.py
"""
Consolidated RAG (Retrieval Augmented Generation) module for ClaimLens.

This module provides:
- Embedding services (Bedrock Titan, HuggingFace, Mock)
- Vector store operations (pgvector, FAISS)
- Document retrieval with hybrid search
- Ingestion pipeline for policy documents

Key exports:
- EmbeddingService: Multi-backend embedding generation
- TitanEmbeddingService: Direct AWS Bedrock Titan embeddings
- RAGRetriever: Main retrieval interface
- FaissStore: FAISS index management
- FaissRetriever: Standalone FAISS retriever
"""

from app.rag.embeddings import EmbeddingService, TitanEmbeddingService
from app.rag.retriever import RAGRetriever, create_rag_retriever
from app.rag.faiss_retriever import FAISSRetriever, get_faiss_retriever
from app.rag.vectorstore.faiss_store import FaissStore
from app.rag.storage.s3_client import S3IndexClient

__all__ = [
    # Embedding services
    "EmbeddingService",
    "TitanEmbeddingService",
    # Retrieval
    "RAGRetriever",
    "create_rag_retriever",
    "FAISSRetriever",
    "get_faiss_retriever",
    # Storage
    "FaissStore",
    "S3IndexClient",
]
