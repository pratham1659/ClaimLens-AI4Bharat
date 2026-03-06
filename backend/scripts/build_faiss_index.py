#!/usr/bin/env python3
"""
ClaimLens FAISS Index Builder
=============================

Builds FAISS vector indexes from policy PDF documents for RAG retrieval.

Usage:
    # From backend directory:
    python scripts/build_faiss_index.py
    
    # Or from project root:
    cd backend && python scripts/build_faiss_index.py

This script will:
1. Load policy PDFs from the data/ directory
2. Extract clauses using the clause splitter
3. Generate embeddings using the local BGE model
4. Build and save FAISS indexes

Author: ClaimLens Team
"""

import os
import sys
import json
from datetime import datetime

# Set up path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
# In Docker container, BACKEND_DIR is /app, and data is at /app/data
# Outside container, PROJECT_ROOT would be parent of backend
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

# Configuration - Check for Docker environment (data at /app/data)
# or local environment (data at PROJECT_ROOT/data)
if os.path.exists(os.path.join(BACKEND_DIR, "data")):
    # Docker container - data is at /app/data
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BACKEND_DIR, "data"))
    INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", os.path.join(
        BACKEND_DIR, "faiss_claimlens_index"))
    COMBINED_INDEX_PATH = os.environ.get("FAISS_COMBINED_INDEX_PATH", os.path.join(
        BACKEND_DIR, "faiss_claimlens_combined_index"))
else:
    # Local development - data is at PROJECT_ROOT/data
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
    INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", os.path.join(
        PROJECT_ROOT, "faiss_claimlens_index"))
    COMBINED_INDEX_PATH = os.environ.get("FAISS_COMBINED_INDEX_PATH", os.path.join(
        PROJECT_ROOT, "faiss_claimlens_combined_index"))
EMBEDDING_MODEL_SIZE = os.environ.get("EMBEDDING_MODEL_SIZE", "base")


def print_banner():
    """Print script banner."""
    print("\n" + "=" * 70)
    print("  ClaimLens FAISS Index Builder")
    print("=" * 70 + "\n")


def load_clauses_from_json(json_path: str) -> list:
    """
    Load pre-extracted clauses from JSON file.

    Args:
        json_path: Path to all_clauses.json

    Returns:
        List of clause documents
    """
    from langchain_core.documents import Document

    print(f"Loading clauses from: {json_path}")

    with open(json_path, 'r') as f:
        clauses_data = json.load(f)

    documents = []
    for clause in clauses_data:
        doc = Document(
            page_content=clause.get("content", clause.get("text", "")),
            metadata={
                "clause_id": clause.get("clause_id", f"clause_{len(documents)}"),
                "insurer": clause.get("insurer", "Unknown"),
                "policy_name": clause.get("policy_name", "Unknown"),
                "section": clause.get("section", ""),
                "clause_number": clause.get("clause_number", ""),
                "clause_title": clause.get("clause_title", ""),
                "chunk_type": clause.get("chunk_type", "clause_level"),
                "source": clause.get("source", ""),
            }
        )
        documents.append(doc)

    print(f"✓ Loaded {len(documents)} clauses from JSON")
    return documents


def extract_clauses_from_pdfs() -> list:
    """
    Extract clauses from policy PDFs.

    Returns:
        List of clause documents
    """
    from app.ingestion.loader import load_policy_documents
    from app.ingestion.clause_splitter import clause_based_splitter

    all_clauses = []

    # Policy configurations
    policies = [
        {
            "file": "icici_complete_health.pdf",
            "insurer": "ICICI Lombard",
            "policy_name": "Complete Health Insurance",
            "uin": "ICIHLIP25035V082425",
            "version_year": 2025
        },
        {
            "file": "niva_rise.pdf",
            "insurer": "Niva Bupa",
            "policy_name": "Rise Health Insurance",
            "uin": "NIVBHLIP24041V012324",
            "version_year": 2024
        }
    ]

    for policy in policies:
        pdf_path = os.path.join(DATA_DIR, policy["file"])

        if not os.path.exists(pdf_path):
            print(f"⚠ Skipping {policy['file']} - file not found")
            continue

        print(f"\nProcessing: {policy['file']}")

        try:
            # Load PDF pages
            docs = load_policy_documents(
                pdf_path=pdf_path,
                insurer=policy["insurer"],
                policy_name=policy["policy_name"],
                uin=policy["uin"],
                policy_version_year=policy["version_year"]
            )
            print(f"  ✓ Loaded {len(docs)} pages")

            # Split into clauses
            clauses = clause_based_splitter(docs)
            print(f"  ✓ Extracted {len(clauses)} clauses")

            all_clauses.extend(clauses)

        except Exception as e:
            print(f"  ✗ Error processing {policy['file']}: {e}")
            import traceback
            traceback.print_exc()

    return all_clauses


def build_faiss_index(clause_documents: list, index_path: str, model_size: str = "base"):
    """
    Build FAISS index from clause documents.

    Args:
        clause_documents: List of clause documents
        index_path: Path to save the index
        model_size: Embedding model size (small, base, large)
    """
    from app.retriever.embeddings import load_embedding_model
    from langchain_community.vectorstores import FAISS

    print(f"\nBuilding FAISS index with {len(clause_documents)} clauses...")
    print(f"  Embedding model size: {model_size}")
    print(f"  Index path: {index_path}")

    # Load embedding model
    print("\n  Loading embedding model...")
    embedding_model = load_embedding_model(model_size=model_size)
    print("  ✓ Embedding model loaded")

    # Build index
    print("\n  Generating embeddings and building index...")
    print("  (This may take a few minutes depending on your hardware)")

    start_time = datetime.now()

    vectorstore = FAISS.from_documents(
        clause_documents,
        embedding_model
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"  ✓ Index built in {elapsed:.1f} seconds")

    # Save index
    print(f"\n  Saving index to: {index_path}")
    vectorstore.save_local(index_path)
    print("  ✓ Index saved")

    return vectorstore


def test_retrieval(vectorstore, test_query: str = "room rent coverage"):
    """
    Test retrieval from the built index.

    Args:
        vectorstore: FAISS vectorstore
        test_query: Query to test
    """
    print(f"\n  Testing retrieval with query: '{test_query}'")

    results = vectorstore.similarity_search(test_query, k=5)

    print(f"  ✓ Retrieved {len(results)} results:\n")

    for i, doc in enumerate(results):
        clause_id = doc.metadata.get("clause_id", "Unknown")
        section = doc.metadata.get("section", "Unknown")
        preview = doc.page_content[:200].replace("\n", " ")
        print(f"    {i+1}. [{clause_id}] {section}")
        print(f"       {preview}...")
        print()


def main():
    """Main entry point."""
    print_banner()

    # Check for pre-extracted clauses JSON
    clauses_json = os.path.join(DATA_DIR, "all_clauses.json")

    if os.path.exists(clauses_json):
        print("Found pre-extracted clauses JSON file.")
        clause_documents = load_clauses_from_json(clauses_json)
    else:
        print("No pre-extracted clauses found. Extracting from PDFs...")
        clause_documents = extract_clauses_from_pdfs()

    if not clause_documents:
        print("\n✗ No clauses to index. Please ensure policy PDFs exist in data/")
        sys.exit(1)

    print(f"\n✓ Total clauses to index: {len(clause_documents)}")

    # Build main index
    print("\n" + "-" * 70)
    print("  BUILDING MAIN INDEX")
    print("-" * 70)

    vectorstore = build_faiss_index(
        clause_documents,
        INDEX_PATH,
        EMBEDDING_MODEL_SIZE
    )

    # Also save as combined index (for compatibility)
    print(f"\n  Saving combined index to: {COMBINED_INDEX_PATH}")
    vectorstore.save_local(COMBINED_INDEX_PATH)
    print("  ✓ Combined index saved")

    # Test retrieval
    print("\n" + "-" * 70)
    print("  TESTING RETRIEVAL")
    print("-" * 70)

    test_queries = [
        "room rent coverage limit",
        "pre-existing disease waiting period",
        "cashless hospitalization network"
    ]

    for query in test_queries:
        test_retrieval(vectorstore, query)

    print("\n" + "=" * 70)
    print("  INDEX BUILD COMPLETE")
    print("=" * 70)
    print(f"\n  Main index: {INDEX_PATH}")
    print(f"  Combined index: {COMBINED_INDEX_PATH}")
    print(f"  Total clauses indexed: {len(clause_documents)}")
    print("\n  You can now use the RAG retriever with these indexes.")
    print("  Start the backend with: ./docker-manage.sh start local")
    print()


if __name__ == "__main__":
    main()
