# backend/app/api/v1/endpoints/policies.py
"""
Policy management endpoints with integrated local RAG support.

This module provides:
- Policy document listing and management
- Semantic search across policy clauses
- Chat with policies using local FAISS + HuggingFace embeddings
- Pre-indexed policy data queries (no upload required)
"""

import logging
import os
import re
import json
import sys
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from pydantic import BaseModel

from app.schemas.document import DocumentResponse
from app.models.document import DocumentType
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.response_formatter import generate_final_response
from app.llm.prompts import POLICY_CHAT_SYSTEM_PROMPT
from app.api.deps import get_document_service, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.document import Document
from app.models.claim import Claim
from app.models.embedding import Embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["Policies"])


# Request/Response models for better API documentation
class ChatRequest(BaseModel):
    """Request model for policy chat."""
    document_id: Optional[str] = None  # Can be UUID string
    message: str
    chat_history: Optional[List[dict]] = None


class PolicyQueryRequest(BaseModel):
    """Request model for querying pre-indexed policies."""
    query: str
    top_k: int = 5


class PolicySearchRequest(BaseModel):
    """Request model for searching policy clauses."""
    query: str
    document_ids: Optional[List[UUID]] = None
    limit: int = 20


class PreindexedIngestRequest(BaseModel):
    """Request model for triggering rag-system preindexed ingestion."""
    use_async: bool = True
    timeout_seconds: int = 900


def _resolve_rag_index_dir() -> Optional[Path]:
    """Resolve the RAG index directory for FAISS indexes and metadata."""
    env_index_dir = os.getenv("RAG_INDEX_DIR", "").strip()
    candidates: List[Path] = []

    if env_index_dir:
        candidates.append(Path(env_index_dir))

    candidates.extend(
        [
            Path(__file__).resolve().parents[5] / "storage" / "indexes",
            Path.cwd() / "storage" / "indexes",
            Path("/app/storage/indexes"),
            Path("/tmp/rag-indexes"),
        ]
    )

    for candidate in candidates:
        if candidate.exists() and (candidate / "faiss.index").exists():
            return candidate.resolve()
        if candidate.exists() and (candidate / "metadata.parquet").exists():
            return candidate.resolve()

    return None


def _search_rag_preindexed(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Search preindexed FAISS bundle using consolidated RAG module."""
    try:
        from app.rag.faiss_retriever import get_faiss_retriever

        retriever = get_faiss_retriever()
        rag_results = retriever.search(query=query, k=top_k)

        mapped_chunks: List[Dict[str, Any]] = []
        for idx, item in enumerate(rag_results):
            mapped_chunks.append(
                {
                    "chunk_id": str(item.get("clause_id") or f"rag_{idx}"),
                    "document_id": "",
                    "chunk_index": int(item.get("rank") or idx),
                    "content": str(item.get("text") or ""),
                    "relevance_score": float(item.get("score_l2") or 0.0),
                    "metadata": {
                        "insurer": item.get("insurer"),
                        "policy_name": item.get("policy_name"),
                        "page": item.get("page"),
                        "section": item.get("section"),
                        "source_pdf": item.get("source_pdf"),
                    },
                    "source": "rag_faiss",
                }
            )

        return mapped_chunks
    except Exception as error:
        logger.warning("RAG preindexed retrieval failed: %s", error)
        return []


def _search_rag_metadata_lexical(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Fallback lexical search over RAG metadata.parquet when semantic retrieval is unavailable."""
    rag_index_dir = _resolve_rag_index_dir()

    index_candidates: List[Path] = []
    if rag_index_dir is not None:
        index_candidates.append(rag_index_dir)
    index_candidates.extend([
        Path("/app/storage/indexes"),
        Path("/tmp/rag-indexes"),
    ])

    metadata_file: Optional[Path] = None
    for candidate in index_candidates:
        candidate_file = candidate / "metadata.parquet"
        if candidate_file.exists():
            metadata_file = candidate_file
            break

    if metadata_file is None:
        return []

    try:
        import pandas as pd

        metadata_df = pd.read_parquet(metadata_file)
        if metadata_df.empty or "text" not in metadata_df.columns:
            return []

        normalized_query = "".join(
            ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in query)
        query_terms = {term for term in normalized_query.split()
                       if len(term) > 2}
        if not query_terms:
            query_terms = {normalized_query.strip(
            )} if normalized_query.strip() else set()

        scored_rows: List[Dict[str, Any]] = []
        for row in metadata_df.to_dict(orient="records"):
            text = str(row.get("text") or "").strip()
            if not text:
                continue

            lowered_text = "".join(ch.lower() if ch.isalnum(
            ) or ch.isspace() else " " for ch in text)
            term_hits = sum(
                1 for term in query_terms if term and term in lowered_text)
            phrase_hit = 2 if normalized_query.strip(
            ) and normalized_query.strip() in lowered_text else 0
            score = term_hits + phrase_hit
            if score <= 0:
                continue

            scored_rows.append(
                {
                    "score": score,
                    "text": text,
                    "metadata": row,
                }
            )

        scored_rows.sort(key=lambda item: item["score"], reverse=True)
        mapped_chunks: List[Dict[str, Any]] = []
        for idx, item in enumerate(scored_rows[: max(1, top_k)]):
            metadata = item["metadata"]
            mapped_chunks.append(
                {
                    "chunk_id": str(metadata.get("clause_id") or f"rag_meta_{idx}"),
                    "document_id": "",
                    "chunk_index": int(metadata.get("chunk_index") or idx),
                    "content": item["text"],
                    "relevance_score": float(item["score"]),
                    "metadata": {
                        "insurer": metadata.get("insurer"),
                        "policy_name": metadata.get("policy_name"),
                        "page": metadata.get("page"),
                        "section": metadata.get("section"),
                        "source_pdf": metadata.get("source_pdf"),
                    },
                    "source": "rag_metadata_lexical",
                }
            )

        return mapped_chunks
    except Exception as error:
        logger.warning("rag metadata lexical fallback failed: %s", error)
        return []


def _deduplicate_retrieval_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove repeated chunks while preserving original ranking order."""
    deduped: List[Dict[str, Any]] = []
    seen_chunk_keys = set()
    seen_content_signatures = set()

    for result in results:
        doc_id = str(result.get("document_id") or "").strip()
        chunk_index = result.get("chunk_index")

        chunk_key = None
        if doc_id and chunk_index is not None:
            chunk_key = (doc_id, int(chunk_index))

        content = str(result.get("content") or "")
        normalized_content = " ".join(content.split()).lower()
        content_signature = normalized_content[:700]

        if chunk_key and chunk_key in seen_chunk_keys:
            continue

        if content_signature and content_signature in seen_content_signatures:
            continue

        if chunk_key:
            seen_chunk_keys.add(chunk_key)
        if content_signature:
            seen_content_signatures.add(content_signature)

        deduped.append(result)

    return deduped


async def _collect_search_diagnostics(db: AsyncSession) -> Dict[str, Any]:
    embedding_count_result = await db.execute(select(func.count(Embedding.id)))
    embedding_count = int(embedding_count_result.scalar() or 0)

    faiss_path = os.getenv("FAISS_INDEX_PATH", "faiss_claimlens_index")
    combined_faiss_path = os.getenv(
        "FAISS_COMBINED_INDEX_PATH", "faiss_claimlens_combined_index")
    clauses_paths = [
        "storage/clauses/all_clauses.json",
        "/app/storage/clauses/all_clauses.json",
        "../storage/clauses/all_clauses.json",
    ]

    return {
        "embedding_rows_in_db": embedding_count,
        "faiss_index_exists": os.path.exists(faiss_path) or os.path.exists(combined_faiss_path),
        "clauses_file_exists": any(os.path.exists(path) for path in clauses_paths),
    }


async def _collect_search_readiness(db: AsyncSession, mode: str) -> Dict[str, Any]:
    diagnostics = await _collect_search_diagnostics(db)
    has_searchable_data = diagnostics["embedding_rows_in_db"] > 0 or diagnostics["faiss_index_exists"]
    return {
        "mode": mode,
        "is_mock_mode": mode == "mock",
        "has_searchable_data": has_searchable_data,
        "ready_for_policy_search": mode != "mock" and has_searchable_data,
        **diagnostics,
    }


@router.get(
    "",
    response_model=List[DocumentResponse],
    summary="List all policy documents"
)
async def list_policies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all insurance policy documents uploaded by the user.
    """
    result = await db.execute(
        select(Document)
        .join(Document.claim)
        .where(Document.document_type == DocumentType.INSURANCE_POLICY)
        .where(Document.claim.has(user_id=current_user.id))
        .order_by(Document.created_at.desc())
    )

    documents = result.scalars().all()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{document_id}/clauses",
    response_model=dict,
    summary="Get policy clauses"
)
async def get_policy_clauses(
    document_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get extracted clauses from a policy document.
    """
    from app.models.embedding import Embedding

    result = await db.execute(
        select(Embedding)
        .where(Embedding.document_id == document_id)
        .order_by(Embedding.chunk_index)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    embeddings = result.scalars().all()

    clauses = [
        {
            "clause_id": str(emb.id),
            "chunk_index": emb.chunk_index,
            "content": emb.chunk_text
        }
        for emb in embeddings
    ]

    return {
        "clauses": clauses,
        "page": page,
        "page_size": page_size
    }


@router.post(
    "/search",
    response_model=dict,
    summary="Search policy clauses"
)
async def search_policies(
    request: PolicySearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search across policy documents using semantic search.
    Automatically uses local FAISS in development or pgvector in production.

    Request body:
    - query: Search query string
    - document_ids: Optional list of document IDs to search within
    - limit: Maximum results (default 20, max 50)
    """
    from app.rag.retriever import create_rag_retriever

    retriever = create_rag_retriever(db)
    readiness = await _collect_search_readiness(db, retriever.embedding_service.mode)

    if retriever.embedding_service.mode == "mock":
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "Policy search is running in mock mode. Set "
                    "USE_MOCK_LLM=false, BEDROCK_ENABLED=true, EMBEDDING_MODE=bedrock, "
                    "and BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0, then restart backend."
                ),
                "readiness": readiness,
            },
        )

    # Ensure limit is within bounds
    limit = min(request.limit, 50)

    if request.document_ids:
        filtered_embedding_count_result = await db.execute(
            select(func.count(Embedding.id)).where(
                Embedding.document_id.in_(request.document_ids))
        )
        filtered_embedding_count = int(
            filtered_embedding_count_result.scalar() or 0)

        if filtered_embedding_count == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "The provided document_ids have no indexed policy embeddings. "
                        "Use valid processed policy document IDs, or omit document_ids to search across all indexed policies."
                    ),
                    "provided_document_ids": [str(doc_id) for doc_id in request.document_ids],
                },
            )

    results = await retriever.retrieve(
        query=request.query,
        document_ids=request.document_ids,
        top_k=limit,
        use_hybrid=True
    )

    results = _deduplicate_retrieval_results(results)
    results = results[:limit]

    if results:
        return {
            "results": results,
            "query": request.query,
            "count": len(results),
            "mode": retriever.embedding_service.mode,
            "readiness": readiness,
        }

    debug_probe: Dict[str, Any] = {"nearest_neighbors": []}
    try:
        query_embedding = await retriever.embedding_service.generate_embedding(request.query)
        nearest_neighbors = await retriever.vector_store.debug_nearest_neighbors(
            query_embedding=query_embedding,
            limit=min(limit, 5),
            document_ids=request.document_ids,
        )
        debug_probe = {
            "nearest_neighbors": nearest_neighbors,
            "document_filter_applied": bool(request.document_ids),
            "result_count": len(nearest_neighbors),
        }
    except Exception as probe_error:
        debug_probe = {
            "nearest_neighbors": [],
            "probe_error": str(probe_error),
        }

    return {
        "results": [],
        "query": request.query,
        "count": 0,
        "mode": retriever.embedding_service.mode,
        "diagnostics": readiness,
        "debug_probe": debug_probe,
        "hint": (
            "No matches found. Ensure policy embeddings are processed into DB or local FAISS preindexed files are available. "
            "You can verify with GET /api/v1/policies/preindexed/info."
        ),
    }


@router.get(
    "/search/readiness",
    response_model=dict,
    summary="Get policy search readiness"
)
async def get_policy_search_readiness(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get policy-search readiness diagnostics for current runtime mode and index/data availability."""
    from app.rag.retriever import create_rag_retriever

    retriever = create_rag_retriever(db)
    readiness = await _collect_search_readiness(db, retriever.embedding_service.mode)
    readiness["hint"] = (
        "Set bedrock mode (non-mock) and ensure either DB embeddings or FAISS preindexed data exists."
    )
    return readiness


@router.post(
    "/process/{document_id}",
    response_model=dict,
    summary="Process policy document with RAG"
)
async def process_policy_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Process an uploaded policy document:
    - Extract text from PDF
    - Split into chunks
    - Generate embeddings
    - Store in vector database
    """
    from app.models.embedding import Embedding

    # Get document and verify ownership
    result = await db.execute(
        select(Document)
        .join(Claim, Document.claim_id == Claim.id)
        .where(Document.id == document_id)
        .where(Claim.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Return existing chunks if already processed
    existing = await db.execute(
        select(Embedding).where(Embedding.document_id == document_id).limit(1)
    )
    if existing.scalar_one_or_none():
        # Return existing chunks
        chunks_result = await db.execute(
            select(Embedding)
            .where(Embedding.document_id == document_id)
            .order_by(Embedding.chunk_index)
        )
        chunks = chunks_result.scalars().all()
        return {
            "success": True,
            "data": {
                "document_id": str(document_id),
                "chunks": [{"content": c.chunk_text, "index": c.chunk_index} for c in chunks]
            }
        }

    # Real processing from uploaded document
    await document_service.process_document(document_id)

    chunks_result = await db.execute(
        select(Embedding)
        .where(Embedding.document_id == document_id)
        .order_by(Embedding.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    return {
        "success": True,
        "data": {
            "document_id": str(document_id),
            "chunks": [{"content": c.chunk_text, "index": c.chunk_index} for c in chunks]
        }
    }


@router.post(
    "/chat",
    response_model=dict,
    summary="Chat with policy document"
)
async def chat_with_policy(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with a processed policy document using RAG.
    Uses local FAISS retriever in development mode.

    If document_id is provided in request, searches that specific document.
    If document_id is not provided, searches pre-indexed policies.
    """
    from app.models.embedding import Embedding
    from app.rag.retriever import create_rag_retriever
    from app.llm.bedrock_client import get_llm_client

    message = request.message
    chat_history = request.chat_history or []

    # Parse document_id if provided
    document_id = None
    if request.document_id:
        try:
            document_id = UUID(request.document_id)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid document_id format: {request.document_id}")

    # First try to get relevant chunks using RAG retriever
    retriever = create_rag_retriever(db)
    retrieved_chunks = []

    # If document_id provided, try to search that document
    if document_id:
        retrieved_chunks = await retriever.retrieve(
            query=message,
            document_ids=[document_id],
            top_k=5,
            use_hybrid=True
        )

    # If no chunks from pgvector or no document_id, try local FAISS (pre-indexed data)
    if not retrieved_chunks and retriever.use_local_faiss:
        logger.info("Using local FAISS retriever for pre-indexed policies")
        retrieved_chunks = await retriever._retrieve_local(message, top_k=5)

    # Fallback to RAG preindexed bundle even when local FAISS mode is disabled.
    if not retrieved_chunks:
        logger.info("Using RAG FAISS fallback for policy chat")
        retrieved_chunks = _search_rag_preindexed(query=message, top_k=5)

    # Final fallback to lexical metadata search when semantic retrieval is unavailable.
    if not retrieved_chunks:
        logger.info("Using RAG metadata lexical fallback for policy chat")
        retrieved_chunks = _search_rag_metadata_lexical(query=message, top_k=5)

    # Build context from retrieved chunks
    context = retriever.build_context(retrieved_chunks)

    if not context and document_id:
        # Fall back to database embeddings for specific document
        chunks_result = await db.execute(
            select(Embedding)
            .where(Embedding.document_id == document_id)
            .order_by(Embedding.chunk_index)
            .limit(5)
        )
        db_chunks = chunks_result.scalars().all()
        context = "\n\n".join([str(c.chunk_text) for c in db_chunks])
        retrieved_chunks = [
            {"content": c.chunk_text, "chunk_index": c.chunk_index,
                "relevance_score": 0.8}
            for c in db_chunks
        ]

    if not context:
        return {
            "success": False,
            "error": "No policy data available. Please process the document first or use pre-indexed policies.",
            "hint": "Upload and process a document, or run POST /api/v1/policies/preindexed/ingest to build the rag-system FAISS index."
        }

    # Get LLM client and generate response
    llm_client = get_llm_client()

    # Build prompt with context
    system_prompt = POLICY_CHAT_SYSTEM_PROMPT

    user_prompt = f"""Context from policy document:
{context}

Supporting clauses retrieved: {len(retrieved_chunks)}

Chat history:
{_format_chat_history(chat_history)}

User question: {message}

Please provide a helpful and accurate answer based on the policy context above."""

    use_grounded_fallback = os.getenv(
        "USE_MOCK_LLM", "false").lower() == "true"

    if use_grounded_fallback:
        answer = _generate_fallback_response(message, retrieved_chunks)
    else:
        try:
            response = await llm_client.invoke(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.3
            )

            answer = response.get(
                "content", "I apologize, but I couldn't generate a response.")

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            answer = _generate_fallback_response(message, retrieved_chunks)

    # Format sources for response
    sources = [
        {
            "content": chunk.get("content", ""),
            "index": chunk.get("chunk_index", i),
            "relevance": chunk.get("relevance_score", 0.5)
        }
        for i, chunk in enumerate(retrieved_chunks[:3])
    ]

    return {
        "success": True,
        "data": {
            "response": answer,
            "sources": sources,
            "mode": retriever.embedding_service.mode
        }
    }


@router.post(
    "/query",
    response_model=dict,
    summary="Query pre-indexed policy documents"
)
async def query_preindexed_policies(
    request: PolicyQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Query pre-indexed policy documents (ICICI, Niva Bupa, etc.) using local FAISS.
    No document upload required - uses pre-built index from data/ folder.
    """
    from app.rag.retriever import create_rag_retriever
    from app.llm.bedrock_client import get_llm_client

    query = request.query
    top_k = request.top_k

    # Create retriever and force local mode
    retriever = create_rag_retriever(db, force_mode="local")

    # Retrieve from local FAISS index
    retrieved_chunks = await retriever._retrieve_local(query, top_k=top_k)

    # Fallback to RAG preindexed bundle if legacy local retriever returns nothing
    if not retrieved_chunks:
        retrieved_chunks = _search_rag_preindexed(query=query, top_k=top_k)

    # Final fallback to lexical metadata search when semantic retrieval is unavailable.
    if not retrieved_chunks:
        retrieved_chunks = _search_rag_metadata_lexical(
            query=query, top_k=top_k)

    if not retrieved_chunks:
        rag_index_dir = _resolve_rag_index_dir()

        return {
            "success": False,
            "error": "No pre-indexed policy data found. Please ensure FAISS index is available.",
            "hint": "Run POST /api/v1/policies/preindexed/ingest to build RAG FAISS index, then retry.",
            "diagnostics": {
                "rag_index_dir": str(rag_index_dir) if rag_index_dir else None,
                "rag_faiss_exists": bool(rag_index_dir and (rag_index_dir / "faiss.index").exists()),
                "rag_metadata_exists": bool(rag_index_dir and (rag_index_dir / "metadata.parquet").exists()),
            },
        }

    # Build context
    context = retriever.build_context(retrieved_chunks)

    # Get LLM response
    llm_client = get_llm_client()

    system_prompt = POLICY_CHAT_SYSTEM_PROMPT

    user_prompt = f"""Retrieved policy clauses:
{context}

Supporting clauses retrieved: {len(retrieved_chunks)}

User query: {query}

Please provide a comprehensive answer based on the policy clauses above."""

    use_grounded_fallback = os.getenv(
        "USE_MOCK_LLM", "false").lower() == "true"

    if use_grounded_fallback:
        answer = _generate_fallback_response(query, retrieved_chunks)
    else:
        try:
            response = await llm_client.invoke(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.3
            )
            answer = response.get("content", "Unable to generate response.")
        except Exception as e:
            logger.error(f"LLM error: {e}")
            answer = _generate_fallback_response(query, retrieved_chunks)

    return {
        "success": True,
        "data": {
            "response": answer,
            "sources": [
                {
                    "content": chunk.get("content", "")[:500],
                    "clause_id": chunk.get("chunk_id", ""),
                    "relevance": chunk.get("relevance_score", 0.5),
                    "insurer": chunk.get("metadata", {}).get("insurer", "Unknown")
                }
                for chunk in retrieved_chunks
            ],
            "query": query,
            "chunks_retrieved": len(retrieved_chunks)
        }
    }


@router.post(
    "/preindexed/ingest",
    response_model=dict,
    summary="Trigger RAG preindexed ingestion"
)
async def ingest_preindexed_policies(
    request: PreindexedIngestRequest = Body(default=PreindexedIngestRequest()),
    current_user: User = Depends(get_current_user),
):
    """Trigger the RAG ingestion pipeline to build FAISS indexes from policy PDFs."""
    try:
        from app.rag.ingestion.rag_pdf_loader import run_ingestion_pipeline
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "RAG ingestion module not available.",
                "error": str(e),
                "hint": "Ensure app.rag.ingestion.pdf_loader is properly installed.",
            },
        )

    # Check for policy directories
    local_policy_dirs_raw = [
        os.getenv("RAG_POLICIES_DIR", "").strip(),
        "storage/policies",
        "/app/storage/policies",
    ]
    local_policy_dirs: List[Path] = []
    seen_dirs = set()
    for raw_dir in local_policy_dirs_raw:
        if not raw_dir:
            continue
        path_obj = Path(raw_dir)
        key = str(path_obj)
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        local_policy_dirs.append(path_obj)

    local_policy_diagnostics = []
    for directory in local_policy_dirs:
        try:
            pdf_count = len(list(directory.glob("*.pdf"))
                            ) if directory.exists() and directory.is_dir() else 0
        except Exception:
            pdf_count = 0

        local_policy_diagnostics.append(
            {
                "path": str(directory),
                "exists": directory.exists(),
                "is_dir": directory.is_dir() if directory.exists() else False,
                "pdf_count": pdf_count,
            }
        )

    try:
        # Determine the root directory for policy discovery
        root_dir = Path.cwd()
        if (Path("/app")).exists():
            root_dir = Path("/app")

        # Run ingestion using the consolidated RAG module
        indexed_count = await asyncio.to_thread(
            run_ingestion_pipeline,
            root_dir=root_dir,
            use_async=request.use_async
        )
    except subprocess.TimeoutExpired as timeout_error:
        raise HTTPException(
            status_code=504,
            detail={
                "message": "RAG ingestion timed out.",
                "timeout_seconds": max(60, int(request.timeout_seconds)),
                "stderr": str(timeout_error)[-1200:],
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "RAG ingestion failed.",
                "error": str(e),
                "diagnostics": {
                    "local_policy_diagnostics": local_policy_diagnostics,
                },
            },
        )

    return {
        "success": True,
        "indexed_clauses": int(indexed_count) if indexed_count else 0,
        "use_async": request.use_async,
        "local_policy_diagnostics": local_policy_diagnostics,
    }


@router.get(
    "/preindexed/info",
    response_model=dict,
    summary="Get info about pre-indexed policies"
)
async def get_preindexed_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about available pre-indexed policy documents.
    """
    ignored_insurer_values = {
        "unknown",
        "n/a",
        "na",
        "none",
        "null",
        "nan",
        "not specified",
    }

    def _is_valid_insurer(value: Optional[str]) -> bool:
        if value is None:
            return False
        normalized = str(value).strip()
        return bool(normalized) and normalized.lower() not in ignored_insurer_values

    # Check multiple paths for clauses file
    clauses_paths = [
        "storage/clauses/all_clauses.json",         # Docker container path
        "/app/storage/clauses/all_clauses.json",     # Docker container absolute path
        "../storage/clauses/all_clauses.json",       # Relative from backend
    ]
    clauses_file = None
    for path in clauses_paths:
        if os.path.exists(path):
            clauses_file = path
            break

    faiss_path = "faiss_claimlens_combined_index"
    alt_faiss_path = "backend/faiss_claimlens_combined_index"
    faiss_exists = os.path.exists(faiss_path) or os.path.exists(alt_faiss_path)

    rag_index_dir = _resolve_rag_index_dir()
    rag_index_candidates: List[Path] = []
    if rag_index_dir is not None:
        rag_index_candidates.append(rag_index_dir)
    rag_index_candidates.extend([
        Path("/app/storage/indexes"),
        Path("/tmp/rag-indexes"),
    ])

    resolved_rag_index_dir: Optional[Path] = None
    rag_faiss_exists = False
    rag_metadata_exists = False
    for candidate in rag_index_candidates:
        faiss_candidate = candidate / "faiss.index"
        metadata_candidate = candidate / "metadata.parquet"
        if faiss_candidate.exists() or metadata_candidate.exists():
            resolved_rag_index_dir = candidate
            rag_faiss_exists = faiss_candidate.exists()
            rag_metadata_exists = metadata_candidate.exists()
            break

    embedding_count_result = await db.execute(select(func.count(Embedding.id)))
    embedding_rows_in_db = int(embedding_count_result.scalar() or 0)
    db_embeddings_exists = embedding_rows_in_db > 0

    info = {
        "available": False,
        "clauses_file_exists": clauses_file is not None,
        "faiss_index_exists": faiss_exists or rag_faiss_exists,
        "db_embeddings_exists": db_embeddings_exists,
        "embedding_rows_in_db": embedding_rows_in_db,
        "policies": [],
        "total_clauses": 0,
        "data_source": "none",
        "rag_index_dir": str(resolved_rag_index_dir) if resolved_rag_index_dir else None,
    }

    # Try to load clauses info
    if clauses_file and os.path.exists(clauses_file):
        try:
            with open(clauses_file, 'r') as f:
                clauses = json.load(f)
                info["total_clauses"] = len(clauses)

                # Get unique insurers
                insurers = set()
                for clause in clauses:
                    insurer = clause.get("insurer")
                    if _is_valid_insurer(insurer):
                        insurers.add(str(insurer).strip())

                info["policies"] = sorted(insurers)
                info["available"] = len(clauses) > 0
                if info["available"]:
                    info["data_source"] = "preindexed_files"
        except Exception as e:
            logger.error(f"Error loading clauses: {e}")

    # Try to load RAG metadata parquet for real pre-indexed count/policies.
    if resolved_rag_index_dir and rag_metadata_exists:
        metadata_file = resolved_rag_index_dir / "metadata.parquet"
        try:
            import pandas as pd

            metadata_df = pd.read_parquet(metadata_file)
            if not metadata_df.empty:
                info["total_clauses"] = int(len(metadata_df))
                if "insurer" in metadata_df.columns:
                    insurers = sorted(
                        {
                            str(value).strip()
                            for value in metadata_df["insurer"].dropna().tolist()
                            if _is_valid_insurer(value)
                        }
                    )
                    if insurers:
                        info["policies"] = insurers

                info["available"] = True
                info["data_source"] = "rag_system_faiss"
        except Exception as e:
            logger.warning(f"Error loading rag-system metadata parquet: {e}")

    # In production, policy search often runs from DB embeddings (pgvector) without local files.
    if db_embeddings_exists:
        info["available"] = True
        if info["total_clauses"] <= 0:
            info["total_clauses"] = embedding_rows_in_db
        if info["data_source"] == "none":
            info["data_source"] = "database_embeddings"

    return info


def _format_chat_history(chat_history: List[dict]) -> str:
    """Format chat history for context."""
    if not chat_history:
        return "No previous conversation."

    formatted = []
    for msg in chat_history[-5:]:  # Last 5 messages
        role = msg.get("role", "user")
        content = msg.get("content", "")
        formatted.append(f"{role.capitalize()}: {content}")

    return "\n".join(formatted)


def _generate_fallback_response(query: str, chunks: List[dict]) -> str:
    """Generate a document-grounded fallback response when LLM is unavailable."""
    if not chunks:
        return generate_final_response(
            query=query,
            clauses=[],
            coverage_explanation=(
                "I could not find matching policy clauses for this question in the retrieved results."
            ),
            plain_language_interpretation=(
                "the available policy text does not clearly answer this yet, so a more specific clause or cleaner document extract is needed"
            ),
        )

    normalized_query = "".join(
        ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in query)
    stopwords = {
        "does", "this", "that", "with", "from", "your", "have", "will", "about",
        "what", "when", "where", "which", "would", "could", "should", "there",
        "their", "then", "than", "into", "policy", "cover", "covered", "coverage",
    }
    query_terms = {
        term for term in normalized_query.split()
        if len(term) > 2 and term not in stopwords
    }
    query_phrase = " ".join(normalized_query.split()).strip()

    intent_keyword_map = {
        "coverage": {"cover", "covered", "coverage", "expenses", "charges", "hospitalization", "icu", "ambulance", "dental", "organ", "plastic"},
        "temporal": {"pre", "post", "before", "after", "days", "hospitalization"},
        "waiting": {"waiting", "period", "preexisting", "pre", "existing", "disease"},
        "cashless": {"cashless", "network", "hospital", "notify", "claim", "process"},
        "domiciliary": {"home", "domiciliary", "treatment", "moved", "beds", "unavailable"},
        "optional": {"air", "ambulance", "restore", "bonus", "benefit", "renew"},
        "definition": {"mean", "means", "define", "definition", "what", "day", "care", "medically", "necessary", "deductible"},
        "exclusion": {"ivf", "cosmetic", "experimental", "outside", "india", "excluded", "exclusion", "not", "covered"},
        "liability": {"maximum", "max", "liability", "limit", "sum", "insured", "policy", "year", "annual"},
    }

    detected_intents = {
        intent
        for intent, keywords in intent_keyword_map.items()
        if any(keyword in normalized_query for keyword in keywords)
    }

    expanded_query_terms = set(query_terms)
    for intent in detected_intents:
        expanded_query_terms.update(intent_keyword_map[intent])

    is_boolean_question = normalized_query.strip().startswith(
        ("does", "are", "is", "can", "will", "if"))

    scored_chunks = []
    for chunk in chunks:
        content = (chunk.get("content") or chunk.get(
            "chunk_text") or "").strip()
        if not content:
            continue
        lowered = "".join(ch.lower() if ch.isalnum()
                          or ch.isspace() else " " for ch in content)

        phrase_hit = 2 if query_phrase and query_phrase in lowered else 0
        term_hits = sum(1 for term in expanded_query_terms if term in lowered)
        intent_hits = sum(
            1
            for intent in detected_intents
            for keyword in intent_keyword_map[intent]
            if keyword in lowered
        )
        score = phrase_hit + term_hits + intent_hits

        scored_chunks.append((score, term_hits + intent_hits, content))

    scored_chunks.sort(key=lambda item: (item[0], item[1]), reverse=True)
    matched_contents = [content for score, _,
                        content in scored_chunks if score > 0][:3]

    if not matched_contents:
        fallback_clauses = [
            (chunk.get("content") or chunk.get("chunk_text") or "").strip()
            for chunk in chunks[:2]
            if (chunk.get("content") or chunk.get("chunk_text") or "").strip()
        ]
        return generate_final_response(
            query=query,
            clauses=fallback_clauses,
            coverage_explanation=(
                "I reviewed the retrieved policy text, but it does not clearly match this question yet."
            ),
            plain_language_interpretation=(
                "this usually means we need a more specific query or the exact clause section to confirm coverage confidently"
            ),
        )

    matched_text = "\n".join(matched_contents).lower()

    liability_intent = "liability" in detected_intents
    coverage_explanation = ""
    plain_language_interpretation = ""

    if liability_intent:
        amount_pattern = re.compile(
            r"(?:rs\.?|inr|₹)\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*\s*(?:lakhs?|lacs?|crores?)\b",
            re.IGNORECASE,
        )
        detected_amounts = []
        for content in matched_contents:
            detected_amounts.extend([m.group(0)
                                    for m in amount_pattern.finditer(content)])

        if detected_amounts:
            unique_amounts = []
            seen_amounts = set()
            for amount in detected_amounts:
                normalized_amount = " ".join(amount.split()).strip(" ,;:")
                normalized_amount = re.sub(
                    r"^(?:inr|rs\.?)\s*", "Rs. ", normalized_amount, flags=re.IGNORECASE)
                normalized_amount = re.sub(
                    r"\s+", " ", normalized_amount).strip()
                dedupe_key = normalized_amount.lower()
                if not normalized_amount or dedupe_key in seen_amounts:
                    continue
                seen_amounts.add(dedupe_key)
                if re.search(r"\d", normalized_amount):
                    unique_amounts.append(normalized_amount)

            amount_text = ", ".join(unique_amounts[:3])
            coverage_explanation = (
                "Based on the retrieved wording, the insurer’s maximum liability appears linked to the stated monetary limits in the policy terms."
            )
            plain_language_interpretation = (
                f"the payable amount is typically capped by limits such as {amount_text}, and remains subject to deductibles, sub-limits, and exclusions"
            )
        else:
            coverage_explanation = (
                "The policy generally treats maximum yearly liability as the total payable amount within the policy limits."
            )
            plain_language_interpretation = (
                "this is usually capped by the Sum Insured in the policy schedule and adjusted by deductibles, sub-limits, and exclusions"
            )
        return generate_final_response(
            query=query,
            clauses=matched_contents,
            coverage_explanation=coverage_explanation,
            plain_language_interpretation=plain_language_interpretation,
        )

    negative_signals = ["not covered", "excluded",
                        "exclusion", "not payable", "not admissible"]
    positive_signals = ["covered", "payable",
                        "eligible", "reimburs", "cashless"]

    negative_hits = sum(
        1 for token in negative_signals if token in matched_text)
    positive_hits = sum(
        1 for token in positive_signals if token in matched_text)

    if negative_hits > positive_hits:
        if is_boolean_question:
            coverage_explanation = (
                "The retrieved wording suggests this scenario is likely not covered in its current form."
            )
        else:
            coverage_explanation = (
                "The matched policy text indicates restrictions or exclusions for this situation."
            )
        plain_language_interpretation = (
            "coverage may still be possible only if a specific exception or optional benefit applies in your schedule"
        )
    elif positive_hits > negative_hits:
        if is_boolean_question:
            coverage_explanation = (
                "The matched policy wording indicates this is likely covered, subject to policy conditions."
            )
        else:
            coverage_explanation = (
                "The policy wording points toward coverage for this query within the stated terms."
            )
        plain_language_interpretation = (
            "you are likely eligible for this benefit, but always verify the exact conditions, limits, and exclusions in your policy schedule"
        )
    else:
        if "definition" in detected_intents:
            coverage_explanation = (
                "The policy wording includes a definition that directly applies to your question."
            )
            plain_language_interpretation = (
                "the definition clause should be read exactly because eligibility decisions often depend on these precise terms"
            )
        elif "waiting" in detected_intents:
            day_values = re.findall(r"\b(\d{1,3})\s*days?\b", matched_text)
            if day_values:
                unique_days = []
                for value in day_values:
                    if value not in unique_days:
                        unique_days.append(value)
                coverage_explanation = (
                    "The retrieved clauses indicate waiting-period based eligibility conditions."
                )
                plain_language_interpretation = (
                    f"the timing conditions appear linked to values such as {', '.join(unique_days[:3])} days, which can affect when benefits become payable"
                )
            else:
                coverage_explanation = (
                    "The policy appears to apply waiting period conditions to this scenario."
                )
                plain_language_interpretation = (
                    "the exact timeline is not fully clear from the top retrieved snippets and should be confirmed against the full clause"
                )
        elif "temporal" in detected_intents:
            day_values = re.findall(r"\b(\d{1,3})\s*days?\b", matched_text)
            if day_values:
                unique_days = []
                for value in day_values:
                    if value not in unique_days:
                        unique_days.append(value)
                coverage_explanation = (
                    "The clause wording suggests this benefit is linked to specific pre/post hospitalization time windows."
                )
                plain_language_interpretation = (
                    f"the applicable timeline appears to include values such as {', '.join(unique_days[:3])} days, subject to the policy conditions"
                )
            else:
                coverage_explanation = (
                    "The policy likely includes timeline-based conditions for this benefit."
                )
                plain_language_interpretation = (
                    "the exact day limits are not clearly visible in the top retrieved snippets and should be confirmed in the full wording"
                )
        else:
            coverage_explanation = (
                "The retrieved text is relevant but does not conclusively confirm coverage for this exact scenario."
            )
            plain_language_interpretation = (
                "coverage will depend on the exact wording, policy limits, exclusions, and your treatment context"
            )

    return generate_final_response(
        query=query,
        clauses=matched_contents,
        coverage_explanation=coverage_explanation,
        plain_language_interpretation=plain_language_interpretation,
    )
