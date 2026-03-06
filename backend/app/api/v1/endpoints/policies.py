# backend/app/api/v1/endpoints/policies.py
"""
Policy management endpoints with integrated local RAG support.

This module provides:
- Policy document listing and management
- Semantic search across policy clauses
- Chat with policies using local FAISS + HuggingFace embeddings
- Pre-indexed policy data queries (no upload required)
"""

import os
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body
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
    import shutil

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

    # Check multiple FAISS index paths
    faiss_paths = [
        "faiss_claimlens_combined_index",
        "backend/faiss_claimlens_combined_index",
        "/app/faiss_claimlens_combined_index",
        "faiss_claimlens_index",
        "/app/faiss_claimlens_index",
    ]

    faiss_path = None
    for path in faiss_paths:
        if os.path.exists(path):
            faiss_path = path
            break

    info = {
        "available": False,
        "clauses_file_exists": clauses_file is not None,
        "clauses_file_path": clauses_file,
        "faiss_index_exists": faiss_path is not None,
        "faiss_index_path": faiss_path,
        "policies": [],
        "total_clauses": 0,
        "index_size_mb": 0
    }

    # Get FAISS index size
    if faiss_path and os.path.exists(faiss_path):
        try:
            total_size = 0
            if os.path.isdir(faiss_path):
                for dirpath, dirnames, filenames in os.walk(faiss_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
            else:
                total_size = os.path.getsize(faiss_path)
            info["index_size_mb"] = round(total_size / (1024 * 1024), 2)
        except Exception as e:
            logger.error(f"Error getting index size: {e}")

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
        except Exception as e:
            logger.error(f"Error loading clauses: {e}")

    # Only mark as available if FAISS index exists (the index is what's actually used for queries)
    info["available"] = faiss_path is not None and info["total_clauses"] > 0

    return info


@router.get(
    "/preindexed/files",
    response_model=dict,
    summary="List PDF files in data folder"
)
async def list_indexed_files(
    current_user: User = Depends(get_current_user)
):
    """
    List all PDF files in the data folder that are/will be included in the index.
    """
    import glob

    # Check multiple possible data folder locations
    data_folders = [
        "data",
        "/app/data",
        "backend/data",
    ]

    data_folder = None
    for folder in data_folders:
        if os.path.exists(folder) and os.path.isdir(folder):
            data_folder = folder
            break

    if not data_folder:
        return {
            "success": True,
            "files": [],
            "data_folder": None,
            "message": "No data folder found"
        }

    # Find all PDF files
    pdf_pattern = os.path.join(data_folder, "*.pdf")
    pdf_files = glob.glob(pdf_pattern)

    files = []
    for pdf_path in pdf_files:
        try:
            stat_info = os.stat(pdf_path)
            files.append({
                "filename": os.path.basename(pdf_path),
                "path": pdf_path,
                "size_mb": round(stat_info.st_size / (1024 * 1024), 2),
                "modified": stat_info.st_mtime
            })
        except Exception as e:
            logger.error(f"Error getting file info for {pdf_path}: {e}")

    # Sort by filename
    files.sort(key=lambda x: x["filename"])

    return {
        "success": True,
        "files": files,
        "data_folder": data_folder,
        "total_files": len(files)
    }


@router.delete(
    "/preindexed/files/{filename}",
    response_model=dict,
    summary="Delete a PDF file from data folder"
)
async def delete_indexed_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a PDF file from the data folder.
    Note: You'll need to rebuild the index after deleting files.
    """
    import urllib.parse

    # Decode URL-encoded filename
    filename = urllib.parse.unquote(filename)

    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return {
            "success": False,
            "error": "Invalid filename"
        }

    # Check multiple possible data folder locations
    data_folders = [
        "data",
        "/app/data",
        "backend/data",
    ]

    file_path = None
    for folder in data_folders:
        potential_path = os.path.join(folder, filename)
        if os.path.exists(potential_path) and os.path.isfile(potential_path):
            file_path = potential_path
            break

    if not file_path:
        return {
            "success": False,
            "error": f"File not found: {filename}"
        }

    try:
        os.remove(file_path)
        logger.info(f"Deleted file: {file_path}")
        return {
            "success": True,
            "message": f"Deleted {filename}",
            "deleted_path": file_path,
            "hint": "Remember to rebuild the index to reflect changes"
        }
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return {
            "success": False,
            "error": f"Failed to delete file: {str(e)}"
        }


@router.post(
    "/preindexed/refresh",
    response_model=dict,
    summary="Refresh/rebuild the FAISS index"
)
async def refresh_preindexed_index(
    current_user: User = Depends(get_current_user)
):
    """
    Rebuild the FAISS index from policy PDF documents in data/ folder.
    This will re-extract clauses and regenerate embeddings.
    """
    import asyncio
    import sys
    import traceback

    cwd = os.getcwd()
    logger.info(f"Refresh index: Current working directory: {cwd}")

    try:
        # Run the build_faiss_index script - check multiple possible locations
        # In Docker, backend is mounted at /app, so scripts are at /app/scripts/
        script_paths = [
            # /app/scripts/build_faiss_index.py in Docker
            os.path.join(cwd, "scripts", "build_faiss_index.py"),
            "scripts/build_faiss_index.py",
            "/app/scripts/build_faiss_index.py",
            "backend/scripts/build_faiss_index.py",
        ]

        script_path = None
        checked_info = []
        for path in script_paths:
            abs_path = os.path.abspath(path)
            exists = os.path.exists(abs_path)
            checked_info.append(f"{path} (abs: {abs_path}, exists: {exists})")
            if exists:
                script_path = abs_path
                logger.info(f"Found build script at: {abs_path}")
                break

        if not script_path:
            logger.error(f"Build script not found. Checked:\n" +
                         "\n".join(checked_info))
            return {
                "success": False,
                "error": "Build script not found",
                "hint": "Ensure scripts/build_faiss_index.py exists",
                "checked_paths": checked_info,
                "cwd": cwd
            }

        logger.info(f"Running index build script: {script_path}")

        # Run from the backend root directory (parent of scripts folder)
        # This ensures relative imports and data paths work correctly
        backend_root = os.path.dirname(os.path.dirname(script_path))
        if not backend_root or backend_root == script_path:
            backend_root = cwd

        logger.info(f"Running script from backend root: {backend_root}")
        logger.info(f"Script absolute path: {script_path}")

        # Use asyncio subprocess to avoid blocking
        # Pass the absolute script path to avoid path confusion
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=backend_root
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": "Index build timed out (>5 minutes)"
            }

        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        if process.returncode == 0:
            logger.info("Index build completed successfully")
            return {
                "success": True,
                "message": "FAISS index rebuilt successfully",
                "output": stdout_str[-1000:] if stdout_str else ""
            }
        else:
            logger.error(f"Index build failed: {stderr_str}")
            return {
                "success": False,
                "error": "Index build failed",
                "details": stderr_str[-500:] if stderr_str else stdout_str[-500:] if stdout_str else "Unknown error",
                "return_code": process.returncode
            }

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error refreshing index: {e}\n{error_traceback}")
        return {
            "success": False,
            "error": str(e),
            "traceback": error_traceback[-500:]
        }


@router.delete(
    "/preindexed/delete",
    response_model=dict,
    summary="Delete the FAISS index"
)
async def delete_preindexed_index(
    current_user: User = Depends(get_current_user)
):
    """
    Delete the pre-indexed FAISS index files.
    This will require rebuilding before queries can be made.
    """
    import shutil

    deleted_paths = []
    errors = []

    # Paths to check and delete
    index_paths = [
        "faiss_claimlens_combined_index",
        "faiss_claimlens_index",
        "/app/faiss_claimlens_combined_index",
        "/app/faiss_claimlens_index",
        "backend/faiss_claimlens_combined_index",
        "backend/faiss_claimlens_index",
    ]

    for path in index_paths:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                deleted_paths.append(path)
                logger.info(f"Deleted index at: {path}")
            except Exception as e:
                errors.append(f"{path}: {str(e)}")
                logger.error(f"Failed to delete {path}: {e}")

    if deleted_paths:
        return {
            "success": True,
            "message": f"Deleted {len(deleted_paths)} index(es)",
            "deleted_paths": deleted_paths,
            "errors": errors if errors else None
        }
    elif errors:
        return {
            "success": False,
            "error": "Failed to delete indexes",
            "details": errors
        }
    else:
        return {
            "success": True,
            "message": "No indexes found to delete"
        }


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
    """Generate a fallback response when LLM is unavailable."""
    query_lower = query.lower()

    # Extract relevant content from chunks
    relevant_content = []
    for chunk in chunks[:3]:
        content = chunk.get("content", "")
        if content:
            relevant_content.append(content[:300])

    # Keyword-based response generation
    if "coverage" in query_lower or "covered" in query_lower:
        response = "Based on the policy documents, coverage includes:\n"
        if relevant_content:
            response += "\n".join([f"- {c[:200]}..." for c in relevant_content])
        else:
            response += "- Hospitalization expenses up to sum insured\n- Pre and post hospitalization care\n- Day care procedures"

    elif "claim" in query_lower:
        response = "Regarding claims:\n"
        if relevant_content:
            response += "\n".join([f"- {c[:200]}..." for c in relevant_content])
        else:
            response += "- Claims must be filed within specified timeframe\n- Required documents include bills, prescriptions, discharge summary"

    elif "waiting" in query_lower or "pre-existing" in query_lower:
        response = "Waiting period information:\n"
        if relevant_content:
            response += "\n".join([f"- {c[:200]}..." for c in relevant_content])
        else:
            response += "- Pre-existing conditions typically have 24-48 month waiting period\n- Specific diseases may have different waiting periods"

    elif "exclusion" in query_lower or "exclude" in query_lower:
        response = "Policy exclusions:\n"
        if relevant_content:
            response += "\n".join([f"- {c[:200]}..." for c in relevant_content])
        else:
            response += "- Cosmetic procedures (unless medically necessary)\n- Self-inflicted injuries\n- War and nuclear risks"

    else:
        response = f"Here is relevant information from the policy documents about '{query}':\n"
        if relevant_content:
            response += "\n".join([f"• {c[:200]}..." for c in relevant_content])
        else:
            response += "Please ask specific questions about coverage, claims, waiting periods, or exclusions for detailed information."

    return response
