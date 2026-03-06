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
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from pydantic import BaseModel

from app.schemas.document import DocumentResponse
from app.schemas.common import SingleResponse
from app.models.document import DocumentType
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.response_formatter import generate_final_response
from app.api.deps import get_document_service, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.document import Document
from app.models.claim import Claim

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

    # Ensure limit is within bounds
    limit = min(request.limit, 50)

    results = await retriever.retrieve(
        query=request.query,
        document_ids=request.document_ids,
        top_k=limit,
        use_hybrid=True
    )

    return {
        "results": results,
        "query": request.query,
        "count": len(results),
        "mode": retriever.embedding_service.mode
    }


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
            "hint": "Upload and process a document, or ensure the FAISS index is built."
        }

    # Get LLM client and generate response
    llm_client = get_llm_client()

    # Build prompt with context
    system_prompt = """You are an expert insurance policy analyst assistant.
Answer questions about insurance policies based on the provided context.
Be precise, cite specific clauses when relevant, and explain in clear language.
If the context doesn't contain enough information, say so clearly."""

    user_prompt = f"""Context from policy document:
{context}

Chat history:
{_format_chat_history(chat_history)}

User question: {message}

Please provide a helpful and accurate answer based on the policy context above."""

    use_grounded_fallback = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

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

    if not retrieved_chunks:
        return {
            "success": False,
            "error": "No pre-indexed policy data found. Please ensure FAISS index is available.",
            "hint": "Run 'python backend/scripts/main.py' to build the index from data/ folder."
        }

    # Build context
    context = retriever.build_context(retrieved_chunks)

    # Get LLM response
    llm_client = get_llm_client()

    system_prompt = """You are an expert insurance policy analyst.
Based on the retrieved policy clauses, provide accurate and helpful information.
Cite specific clause numbers and policy names when available."""

    user_prompt = f"""Retrieved policy clauses:
{context}

User query: {query}

Please provide a comprehensive answer based on the policy clauses above."""

    use_grounded_fallback = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

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


@router.get(
    "/preindexed/info",
    response_model=dict,
    summary="Get info about pre-indexed policies"
)
async def get_preindexed_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get information about available pre-indexed policy documents.
    """
    import json

    # Check multiple paths for clauses file
    clauses_paths = [
        "data/all_clauses.json",         # Docker container path
        "/app/data/all_clauses.json",     # Docker container absolute path
        "../data/all_clauses.json",       # Relative from backend
    ]
    clauses_file = None
    for path in clauses_paths:
        if os.path.exists(path):
            clauses_file = path
            break

    faiss_path = "faiss_claimlens_combined_index"
    alt_faiss_path = "backend/faiss_claimlens_combined_index"

    info = {
        "available": False,
        "clauses_file_exists": clauses_file is not None,
        "faiss_index_exists": os.path.exists(faiss_path) or os.path.exists(alt_faiss_path),
        "policies": [],
        "total_clauses": 0
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
                    insurer = clause.get("insurer", "Unknown")
                    insurers.add(insurer)

                info["policies"] = list(insurers)
                info["available"] = len(clauses) > 0
        except Exception as e:
            logger.error(f"Error loading clauses: {e}")

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

    normalized_query = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in query)
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

    is_boolean_question = normalized_query.strip().startswith(("does", "are", "is", "can", "will", "if"))

    scored_chunks = []
    for chunk in chunks:
        content = (chunk.get("content") or chunk.get("chunk_text") or "").strip()
        if not content:
            continue
        lowered = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in content)

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
    matched_contents = [content for score, _, content in scored_chunks if score > 0][:3]

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
        amount_pattern = re.compile(r"(?:rs\.?|inr|₹)\s*[\d,]+(?:\.\d+)?|[\d,]+\s*(?:lakhs?|lacs?|crores?)", re.IGNORECASE)
        detected_amounts = []
        for content in matched_contents:
            detected_amounts.extend([m.group(0) for m in amount_pattern.finditer(content)])

        if detected_amounts:
            unique_amounts = []
            for amount in detected_amounts:
                normalized_amount = " ".join(amount.split())
                if normalized_amount not in unique_amounts:
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

    negative_signals = ["not covered", "excluded", "exclusion", "not payable", "not admissible"]
    positive_signals = ["covered", "payable", "eligible", "reimburs", "cashless"]

    negative_hits = sum(1 for token in negative_signals if token in matched_text)
    positive_hits = sum(1 for token in positive_signals if token in matched_text)

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
            "the final payable amount still depends on limits, waiting periods, deductibles, and exclusions"
        )
    else:
        if "definition" in detected_intents:
            coverage_explanation = (
                "This question appears to be definition-based, and the policy wording provides the governing definition."
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
