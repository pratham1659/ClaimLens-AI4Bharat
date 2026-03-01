#!/usr/bin/env python3
"""
ClaimLens RAG - Retrieval Test Script

Tests hybrid retrieval (Dense + BM25 + optional reranker).

Environment Variables:
    DATA_DIR: Path to data directory (default: ./data)
    EMBEDDING_MODEL_SIZE: small/base/large (default: base)
    DENSE_TOP_K: Dense candidate count (default: 40)
    USE_RERANKER: true/false (default: false)
    TOP_K: Number of final results to display (default: 5)
"""

import os
import sys

from app.rag_main.ingestion.loader import load_policy_documents
from app.rag_main.ingestion.clause_splitter import health_policy_splitter
from app.rag_main.retrieval.embeddings import load_embedding_model
from app.rag_main.retrieval.retriever import ClaimLensRetriever


DATA_DIR = os.environ.get("DATA_DIR", "data")
EMBEDDING_MODEL_SIZE = os.environ.get("EMBEDDING_MODEL_SIZE", "base")
DENSE_TOP_K = int(os.environ.get("DENSE_TOP_K", "40"))
USE_RERANKER = os.environ.get("USE_RERANKER", "false").lower() == "true"
TOP_K_RESULTS = int(os.environ.get("TOP_K", "5"))
POLICY = os.environ.get("POLICY", "icici")


def print_banner():
    print("\n" + "=" * 70)
    print(" ClaimLens - Retrieval Test")
    print("=" * 70)
    print(f" Model Size:    {EMBEDDING_MODEL_SIZE}")
    print(f" Dense Top-K:   {DENSE_TOP_K}")
    print(f" Use Reranker:  {USE_RERANKER}")
    print(f" Top Results:   {TOP_K_RESULTS}")
    print(f" Policy:        {POLICY}")
    print("=" * 70 + "\n")


def print_clause(clause, rank: int):
    print(f"\n{'─' * 70}")
    print(f" Rank: {rank}")
    print(f" Insurer: {clause.metadata.get('insurer', 'N/A')}")
    print(f" Clause ID: {clause.metadata.get('clause_id', 'N/A')}")
    print(f" Start Page: {clause.metadata.get('start_page', 'N/A')}")
    print("\n Preview:")

    preview = clause.page_content[:500].replace("\n", "\n    ")
    print(f"    {preview}")

    if len(clause.page_content) > 500:
        print(f"    ... ({len(clause.page_content) - 500} more characters)")

    print(f"{'─' * 70}")


def load_documents():
    documents = {}

    icici_path = os.path.join(DATA_DIR, "icici_complete_health.pdf")
    niva_path = os.path.join(DATA_DIR, "niva_rise.pdf")

    if os.path.exists(icici_path):
        print("Loading ICICI policy...")
        documents["icici"] = load_policy_documents(
            pdf_path=icici_path,
            insurer="ICICI Lombard",
            policy_name="Complete Health Insurance",
            uin="ICIHLIP25035V082425",
            policy_version_year=2025,
        )
        print(f"  ✓ {len(documents['icici'])} pages loaded")

    if os.path.exists(niva_path):
        print("Loading Niva policy...")
        documents["niva"] = load_policy_documents(
            pdf_path=niva_path,
            insurer="Niva Bupa",
            policy_name="Rise Policy",
            uin="NIVHLIPXXXX",
            policy_version_year=2025,
        )
        print(f"  ✓ {len(documents['niva'])} pages loaded")

    if not documents:
        print("No policy PDFs found.")
        sys.exit(1)

    return documents


def select_documents(documents: dict):
    policy = POLICY.lower()

    if policy == "icici":
        return documents.get("icici", [])
    elif policy == "niva":
        return documents.get("niva", [])
    elif policy == "both":
        return documents.get("icici", []) + documents.get("niva", [])
    else:
        raise ValueError("POLICY must be: icici, niva, both")



def main():

    print_banner()

    test_queries = [
        "Information about IVF",
        "What is grace period?",
        "What are ICU charges?",
    ]

    print("Loading documents...")
    documents = load_documents()

    docs = select_documents(documents)
    print(f"\nTotal pages to process: {len(docs)}")

    print("\nSplitting into clauses...")
    clause_docs = health_policy_splitter(docs)
    print(f"Total clauses extracted: {len(clause_docs)}")

    print(f"\nLoading embedding model ({EMBEDDING_MODEL_SIZE})...")
    embedding_model = load_embedding_model(model_size=EMBEDDING_MODEL_SIZE)

    print("\nBuilding hybrid retriever...")
    retriever = ClaimLensRetriever(
        clause_documents=clause_docs,
        embedding_model=embedding_model,
        index_path="faiss_claimlens_index",
        dense_top_k=DENSE_TOP_K,
        use_reranker=USE_RERANKER,
    )

    print("\n" + "=" * 70)
    print(" RUNNING RETRIEVAL TESTS")
    print("=" * 70)

    for query in test_queries:

        print("\n" + "#" * 70)
        print(f" QUERY: {query}")
        print("#" * 70)

        retrieved_docs = retriever.retrieve(query)
        top_results = retrieved_docs[:TOP_K_RESULTS]

        print(f"\nRetrieved {len(top_results)} clauses:")

        for rank, clause in enumerate(top_results, start=1):
            print_clause(clause, rank)

    print("\n" + "=" * 70)
    print(" RETRIEVAL TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()