#!/usr/bin/env python3
"""
ClaimLens RAG Test Retrieval Script
====================================

This script tests the hybrid retrieval system (Dense + BM25) with sample 
insurance policy queries. It demonstrates the full RAG pipeline:

1. Loads policy documents (ICICI Complete Health, Niva Bupa Rise)
2. Splits documents into semantic clauses
3. Builds/loads FAISS vector index with HuggingFace embeddings
4. Runs hybrid retrieval (dense + BM25 + optional reranking)
5. Displays top-k relevant clauses for each query

Environment Variables:
    EMBEDDING_MODEL_SIZE: Model size (small/base/large), default: base
    DENSE_TOP_K: Number of candidates from dense retrieval, default: 20
    USE_RERANKER: Enable cross-encoder reranking (true/false), default: false
    
Usage:
    cd backend && python3 scripts/test_retrieval.py
    # or
    ./scripts/run_rag.sh test

Author: ClaimLens Team
"""

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import clause_based_splitter
from app.retriever.embeddings import load_embedding_model
from app.retriever.retriever import ClaimLensRetriever
import sys
import os

# Set up path for imports BEFORE importing app modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

# Configuration from environment
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
EMBEDDING_MODEL_SIZE = os.environ.get("EMBEDDING_MODEL_SIZE", "base")
DENSE_TOP_K = int(os.environ.get("DENSE_TOP_K", "20"))
USE_RERANKER = os.environ.get("USE_RERANKER", "false").lower() == "true"
TOP_K_RESULTS = int(os.environ.get("TOP_K", "5"))

# Now import app modules


def print_banner():
    """Print script banner."""
    print("\n" + "=" * 70)
    print("  ClaimLens RAG - Retrieval Test")
    print("=" * 70)
    print(f"  Model Size:    {EMBEDDING_MODEL_SIZE}")
    print(f"  Dense Top-K:   {DENSE_TOP_K}")
    print(f"  Use Reranker:  {USE_RERANKER}")
    print(f"  Top Results:   {TOP_K_RESULTS}")
    print("=" * 70 + "\n")


def print_clause(clause, rank: int):
    """
    Pretty-print a retrieved clause with metadata.

    Args:
        clause: LangChain Document with metadata
        rank: Result rank (1-indexed)
    """
    print(f"\n{'─' * 70}")
    print(f"  Rank: {rank}")
    print(f"  Insurer: {clause.metadata.get('insurer', 'N/A')}")
    print(f"  Section: {clause.metadata.get('section', 'N/A')}")
    print(f"  Clause Number: {clause.metadata.get('clause_number', 'N/A')}")
    print(f"  Clause Title: {clause.metadata.get('clause_title', 'N/A')}")
    print(f"  Clause ID: {clause.metadata.get('clause_id', 'N/A')}")
    print(f"  Start Page: {clause.metadata.get('start_page', 'N/A')}")
    print(f"\n  Preview:")
    # Show first 500 chars with proper indentation
    preview = clause.page_content[:500].replace('\n', '\n    ')
    print(f"    {preview}")
    if len(clause.page_content) > 500:
        print(f"    ... ({len(clause.page_content) - 500} more characters)")
    print(f"{'─' * 70}")


def load_documents():
    """
    Load policy documents from PDF files.

    Returns:
        dict: Mapping of policy name to list of documents
    """
    documents = {}

    # ICICI Complete Health Insurance
    icici_path = os.path.join(DATA_DIR, "icici_complete_health.pdf")
    if os.path.exists(icici_path):
        print("Loading ICICI Complete Health Insurance...")
        documents["icici"] = load_policy_documents(
            pdf_path=icici_path,
            insurer="ICICI Lombard",
            policy_name="Complete Health Insurance",
            uin="ICIHLIP25035V082425",
            policy_version_year=2025
        )
        print(f"  ✓ Loaded {len(documents['icici'])} pages")
    else:
        print(f"  ⚠ ICICI policy not found at {icici_path}")

    # Niva Bupa Rise
    niva_path = os.path.join(DATA_DIR, "niva_rise.pdf")
    if os.path.exists(niva_path):
        print("Loading Niva Bupa Rise Policy...")
        documents["niva"] = load_policy_documents(
            pdf_path=niva_path,
            insurer="Niva Bupa",
            policy_name="Rise Policy",
            uin="NIVHLIPXXXX",
            policy_version_year=2025
        )
        print(f"  ✓ Loaded {len(documents['niva'])} pages")
    else:
        print(f"  ⚠ Niva policy not found at {niva_path}")

    return documents


def get_combined_docs(documents: dict, policy: str = "both") -> list:
    """
    Get combined documents based on policy selection.

    Args:
        documents: Dict of loaded documents
        policy: Policy selection ('icici', 'niva', 'both')

    Returns:
        List of documents
    """
    policy = policy.lower()
    if policy == "icici":
        return documents.get("icici", [])
    elif policy == "niva":
        return documents.get("niva", [])
    elif policy == "both":
        return documents.get("icici", []) + documents.get("niva", [])
    else:
        raise ValueError(
            f"Invalid policy: {policy}. Choose: icici, niva, both")


def main():
    """Main entry point for retrieval testing."""
    print_banner()

    # Sample queries for testing insurance policy retrieval
    test_queries = [
        "What is the Grace Period?",
        "What is Re-fill benefit?",
        "What is the moratorium period?",
        "Is organ donor covered?",
        "What is the definition of Hospital?",
        "What are the conditions for renewal of the policy?",
    ]

    # Load documents
    print("Loading policy documents...")
    documents = load_documents()

    if not documents:
        print("Error: No documents loaded!")
        sys.exit(1)

    # Combine documents
    policy = os.environ.get("POLICY", "both")
    docs = get_combined_docs(documents, policy)
    print(f"\nTotal pages to process: {len(docs)}")

    # Split into clauses
    print("\nSplitting into clauses...")
    clause_docs = clause_based_splitter(docs)
    print(f"Total clauses extracted: {len(clause_docs)}")

    # Load embedding model
    print(f"\nLoading embedding model ({EMBEDDING_MODEL_SIZE})...")
    embedding_model = load_embedding_model(model_size=EMBEDDING_MODEL_SIZE)

    # Build retriever
    print("\nBuilding hybrid retriever...")
    retriever = ClaimLensRetriever(
        clause_documents=clause_docs,
        embedding_model=embedding_model,
        index_path=os.path.join(BACKEND_DIR, "faiss_claimlens_index"),
        dense_top_k=DENSE_TOP_K,
        use_reranker=USE_RERANKER
    )

    # Run queries
    print("\n" + "=" * 70)
    print("  RUNNING RETRIEVAL TESTS")
    print("=" * 70)

    for query in test_queries:
        print("\n" + "#" * 70)
        print(f"  QUERY: {query}")
        print("#" * 70)

        # Retrieve relevant clauses
        retrieved_docs = retriever.retrieve(query)

        # Show top results
        top_results = retrieved_docs[:TOP_K_RESULTS]
        print(f"\n  Retrieved {len(top_results)} clauses:")

        for rank, clause in enumerate(top_results, start=1):
            print_clause(clause, rank)

    print("\n" + "=" * 70)
    print("  RETRIEVAL TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
