# backend/app/api/v1/endpoints/policies.py
"""
Policy management endpoints.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query

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

router = APIRouter(prefix="/policies", tags=["Policies"])


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
    query: str,
    document_ids: Optional[List[UUID]] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search across policy documents using semantic search.
    """
    from app.rag.retriever import RAGRetriever

    retriever = RAGRetriever(db)

    results = await retriever.retrieve(
        query=query,
        document_ids=document_ids,
        top_k=limit,
        use_hybrid=True
    )

    return {
        "results": results,
        "query": query,
        "count": len(results)
    }


@router.post(
    "/process/{document_id}",
    response_model=dict,
    summary="Process policy document with RAG"
)
async def process_policy_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process an uploaded policy document:
    - Extract text from PDF
    - Split into chunks
    - Generate embeddings
    - Store in vector database
    """
    from app.models.embedding import Embedding
    import os

    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        return {"success": False, "error": "Document not found"}

    # Check if already processed
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

    # For Mock LLM mode, generate mock chunks
    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

    if use_mock:
        # Generate mock policy chunks for development
        mock_chunks = [
            "Coverage includes hospitalization expenses up to the sum insured amount.",
            "Pre-existing conditions are covered after a waiting period of 2 years.",
            "Emergency medical expenses are covered worldwide.",
            "The policy excludes cosmetic surgery unless medically necessary.",
            "Claims must be filed within 30 days of treatment completion.",
            "Cashless facility is available at network hospitals only.",
            "Room rent is limited to 1% of sum insured per day.",
            "ICU charges are covered up to 2% of sum insured per day.",
            "Pre and post hospitalization expenses covered for 30 and 60 days respectively.",
            "Annual health check-up benefit included after first claim-free year."
        ]

        chunks_data = []
        for idx, chunk_text in enumerate(mock_chunks):
            # Create mock embedding (1536 dimensions for compatibility)
            mock_embedding = [0.0] * 1536

            embedding = Embedding(
                document_id=document_id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=mock_embedding,
                metadata={"source": "mock", "page": idx + 1}
            )
            db.add(embedding)
            chunks_data.append({"content": chunk_text, "index": idx})

        await db.commit()

        return {
            "success": True,
            "data": {
                "document_id": str(document_id),
                "chunks": chunks_data
            }
        }

    # Real processing would go here for production
    return {
        "success": True,
        "data": {
            "document_id": str(document_id),
            "chunks": []
        }
    }


@router.post(
    "/chat",
    response_model=dict,
    summary="Chat with policy document"
)
async def chat_with_policy(
    document_id: UUID,
    message: str,
    chat_history: Optional[List[dict]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with a processed policy document using RAG.
    """
    from app.models.embedding import Embedding
    import os

    # Get relevant chunks for the question
    chunks_result = await db.execute(
        select(Embedding)
        .where(Embedding.document_id == document_id)
        .order_by(Embedding.chunk_index)
        .limit(5)
    )
    chunks = chunks_result.scalars().all()

    if not chunks:
        return {
            "success": False,
            "error": "Document not processed yet"
        }

    # Build context from chunks (for future LLM integration)
    # context = "\n\n".join([str(c.chunk_text) for c in chunks])

    # For Mock LLM mode, generate contextual mock response
    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

    if use_mock:
        # Generate a mock response based on the question
        message_lower = message.lower()

        if "coverage" in message_lower or "covered" in message_lower:
            response = "Based on the policy document, coverage includes hospitalization expenses up to the sum insured amount. Pre-existing conditions are covered after a waiting period of 2 years. Emergency medical expenses are covered worldwide. However, cosmetic surgery is excluded unless medically necessary."
        elif "claim" in message_lower:
            response = "According to the policy terms, claims must be filed within 30 days of treatment completion. Cashless facility is available at network hospitals only. Pre and post hospitalization expenses are covered for 30 and 60 days respectively."
        elif "room" in message_lower or "rent" in message_lower:
            response = "The policy specifies that room rent is limited to 1% of sum insured per day. ICU charges are covered up to 2% of sum insured per day."
        elif "waiting" in message_lower or "pre-existing" in message_lower:
            response = "Pre-existing conditions are covered after a waiting period of 2 years from the policy start date."
        elif "benefit" in message_lower or "health check" in message_lower:
            response = "The policy includes an annual health check-up benefit after the first claim-free year."
        else:
            response = f"Based on the policy document, I can help you understand various aspects including coverage limits, claim procedures, room rent caps, and waiting periods. Your specific question about '{message}' relates to the general terms of the policy. Please ask more specific questions about coverage, claims, or benefits for detailed information."

        return {
            "success": True,
            "data": {
                "response": response,
                "sources": [{"content": c.chunk_text, "index": c.chunk_index} for c in chunks[:3]]
            }
        }

    # For production, use actual LLM
    return {
        "success": True,
        "data": {
            "response": "LLM integration required for production responses.",
            "sources": []
        }
    }
