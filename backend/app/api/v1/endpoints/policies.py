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
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from pydantic import BaseModel

from app.schemas.document import DocumentResponse
from app.schemas.common import SingleResponse
from app.models.document import DocumentType
from app.models.user import User
from app.services.document_service import DocumentService
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
        return (
            "I couldn’t find matching policy clauses for your question. "
            "Please ask with clear keywords like ambulance, dental, waiting period, or room rent, "
            "or upload a clearer insurance policy PDF."
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
        return (
            f"I checked your policy, but I couldn’t find clear clauses matching '{query.strip()}'. "
            "Try asking in a more specific way, for example: "
            "‘Is ambulance covered under hospitalization?’, ‘Is dental excluded?’, or ‘What is the waiting period?’"
        )

    matched_text = "\n".join(matched_contents).lower()

    liability_intent = "liability" in detected_intents

    if liability_intent:
        import re

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
            short_answer = (
                f"Short answer: based on the extracted clauses, the policy’s maximum insurer liability appears tied to these stated limits: {amount_text}. "
                "This is still subject to deductibles, sub-limits, and exclusions."
            )
        else:
            short_answer = (
                "Short answer: the insurer’s maximum liability for a policy year is the total amount payable under the policy terms, "
                "typically capped by the Sum Insured shown in the Policy Schedule, and reduced by deductibles/sub-limits/exclusions."
            )

        evidence_lines = []
        for index, content in enumerate(matched_contents[:3], start=1):
            snippet = " ".join(content.split())
            if len(snippet) > 220:
                snippet = f"{snippet[:220].rstrip()}..."
            evidence_lines.append(f"{index}) {snippet}")

        evidence_block = "\n".join(evidence_lines)

        return (
            f"{short_answer}\n\n"
            "Here’s the policy wording I found:\n"
            f"{evidence_block}\n\n"
            "If you share the Sum Insured value from your Policy Schedule, I can map this to an exact yearly liability amount."
        )

    negative_signals = ["not covered", "excluded", "exclusion", "not payable", "not admissible"]
    positive_signals = ["covered", "payable", "eligible", "reimburs", "cashless"]

    negative_hits = sum(1 for token in negative_signals if token in matched_text)
    positive_hits = sum(1 for token in positive_signals if token in matched_text)

    if negative_hits > positive_hits:
        if is_boolean_question:
            short_answer = (
                "Short answer: likely no for this scenario, because the matched clauses indicate exclusions or restrictions."
            )
        else:
            short_answer = (
                "Short answer: this looks restricted or not covered in the clauses I found, "
                "unless there is a specific exception."
            )
    elif positive_hits > negative_hits:
        if is_boolean_question:
            short_answer = (
                "Short answer: likely yes, this appears covered based on the matched clauses, subject to limits/waiting period/exclusions."
            )
        else:
            short_answer = (
                "Short answer: this looks covered, but policy conditions still apply "
                "(limits, waiting period, and exclusions)."
            )
    else:
        if "definition" in detected_intents:
            short_answer = (
                "Short answer: this appears to be defined in the policy text below; wording should be read exactly as given in the clause."
            )
        elif "waiting" in detected_intents:
            import re

            day_values = re.findall(r"\b(\d{1,3})\s*days?\b", matched_text)
            if day_values:
                unique_days = []
                for value in day_values:
                    if value not in unique_days:
                        unique_days.append(value)
                short_answer = (
                    f"Short answer: waiting/eligibility appears time-bound in the matched clauses (noted values: {', '.join(unique_days[:3])} days)."
                )
            else:
                short_answer = (
                    "Short answer: waiting period conditions apply, but the exact timeline needs confirmation from the specific clause wording."
                )
        elif "temporal" in detected_intents:
            import re

            day_values = re.findall(r"\b(\d{1,3})\s*days?\b", matched_text)
            if day_values:
                unique_days = []
                for value in day_values:
                    if value not in unique_days:
                        unique_days.append(value)
                short_answer = (
                    f"Short answer: this appears covered within specific time windows (detected: {', '.join(unique_days[:3])} days), subject to policy conditions."
                )
            else:
                short_answer = (
                    "Short answer: the policy seems to include pre/post hospitalization timing rules, but exact day limits are not clearly visible in top matches."
                )
        else:
            short_answer = (
                "Short answer: the wording is unclear for this exact question, "
                "so coverage depends on conditions and exclusions."
            )

    evidence_lines = []
    for index, content in enumerate(matched_contents[:3], start=1):
        snippet = " ".join(content.split())
        if len(snippet) > 220:
            snippet = f"{snippet[:220].rstrip()}..."
        evidence_lines.append(f"{index}) {snippet}")

    evidence_block = "\n".join(evidence_lines)

    return (
        f"{short_answer}\n\n"
        "Here’s what I found in your policy:\n"
        f"{evidence_block}\n\n"
        "Next step: share the exact treatment/procedure and hospitalization details, "
        "and I’ll give you a clearer policy-based answer."
    )
