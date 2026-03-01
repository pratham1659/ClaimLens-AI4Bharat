#!/usr/bin/env python3
"""
ClaimLens RAG Evaluation Script
===============================

This script runs comprehensive evaluation metrics on the retrieval system
using a benchmark query set with ground-truth relevant clauses.

Metrics Calculated:
- Recall@K: Fraction of relevant clauses retrieved in top-K results
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
- Precision@K: Fraction of top-K results that are relevant
- NDCG@K: Normalized Discounted Cumulative Gain

Input:
    data/evaluation_queries.json - JSON file with queries and ground truth
    
Environment Variables:
    EMBEDDING_MODEL_SIZE: Model size (small/base/large), default: base
    DENSE_TOP_K: Number of candidates from dense retrieval, default: 40
    USE_RERANKER: Enable cross-encoder reranking (true/false), default: true
    
Usage:
    cd backend && python3 scripts/run_evaluation.py
    # or
    ./scripts/run_rag.sh eval

Author: ClaimLens Team
"""

from app.rag_main.ingestion.loader import load_policy_documents
from app.rag_main.ingestion.clause_splitter import clause_based_splitter
from app.rag_main.retrieval.embeddings import load_embedding_model
from app.rag_main.retrieval.retriever import ClaimLensRetriever
from app.rag_main.evaluation.evaluator import RetrievalEvaluator
import sys
import os
import json

# Set up path for imports BEFORE importing app modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

# Configuration from environment
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
EMBEDDING_MODEL_SIZE = os.environ.get("EMBEDDING_MODEL_SIZE", "base")
DENSE_TOP_K = int(os.environ.get("DENSE_TOP_K", "40"))
USE_RERANKER = os.environ.get("USE_RERANKER", "true").lower() == "true"

# Now import app modules


def print_banner():
    """Print script banner."""
    print("\n" + "=" * 70)
    print("  ClaimLens RAG - Retrieval Evaluation")
    print("=" * 70)
    print(f"  Model Size:    {EMBEDDING_MODEL_SIZE}")
    print(f"  Dense Top-K:   {DENSE_TOP_K}")
    print(f"  Use Reranker:  {USE_RERANKER}")
    print("=" * 70 + "\n")


def load_documents():
    """
    Load policy documents from PDF files.

    Returns:
        list: Combined list of documents from all policies
    """
    all_docs = []

    # ICICI Complete Health Insurance
    icici_path = os.path.join(DATA_DIR, "icici_complete_health.pdf")
    if os.path.exists(icici_path):
        print("Loading ICICI Complete Health Insurance...")
        docs = load_policy_documents(
            pdf_path=icici_path,
            insurer="ICICI Lombard",
            policy_name="Complete Health Insurance",
            uin="ICIHLIP25035V082425",
            policy_version_year=2025
        )
        all_docs.extend(docs)
        print(f"  ✓ Loaded {len(docs)} pages")

    # Niva Bupa Rise
    niva_path = os.path.join(DATA_DIR, "niva_rise.pdf")
    if os.path.exists(niva_path):
        print("Loading Niva Bupa Rise Policy...")
        docs = load_policy_documents(
            pdf_path=niva_path,
            insurer="Niva Bupa",
            policy_name="Rise Policy",
            uin="NIVHLIPXXXX",
            policy_version_year=2025
        )
        all_docs.extend(docs)
        print(f"  ✓ Loaded {len(docs)} pages")

    return all_docs


def load_evaluation_queries():
    """
    Load evaluation queries from JSON file.

    Returns:
        list: List of evaluation query objects with ground truth
    """
    eval_path = os.path.join(DATA_DIR, "evaluation_queries.json")

    if not os.path.exists(eval_path):
        print(f"Error: Evaluation queries file not found at {eval_path}")
        print("\nExpected format:")
        print('''[
    {
        "query": "What is the grace period?",
        "relevant_clause_ids": ["clause_123", "clause_456"]
    }
]''')
        sys.exit(1)

    with open(eval_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"\n✓ Loaded {len(queries)} evaluation queries")
    return queries


def print_results(results: dict):
    """
    Pretty-print evaluation results.

    Args:
        results: Dictionary of metric names to values
    """
    print("\n" + "=" * 50)
    print("  EVALUATION RESULTS")
    print("=" * 50)

    # Define display order and descriptions
    metrics_info = {
        "recall@5": "Recall@5 - % of relevant clauses in top 5",
        "recall@10": "Recall@10 - % of relevant clauses in top 10",
        "recall@20": "Recall@20 - % of relevant clauses in top 20",
        "mrr": "MRR - Mean Reciprocal Rank",
        "precision@5": "Precision@5 - % of top 5 that are relevant",
        "precision@10": "Precision@10 - % of top 10 that are relevant",
        "ndcg@10": "NDCG@10 - Normalized DCG at 10",
        "hit_rate@5": "Hit Rate@5 - Queries with ≥1 relevant in top 5",
    }

    for metric_key, description in metrics_info.items():
        if metric_key in results:
            value = results[metric_key]
            # Format as percentage for most metrics
            if "recall" in metric_key or "precision" in metric_key or "hit_rate" in metric_key:
                print(f"  {description}: {value:.1%}")
            else:
                print(f"  {description}: {value:.4f}")

    # Print any additional metrics not in our list
    for key, value in results.items():
        if key.lower() not in metrics_info:
            print(f"  {key}: {value:.4f}")

    print("=" * 50 + "\n")


def main():
    """Main entry point for evaluation."""
    print_banner()

    # Load documents
    print("Loading policy documents...")
    docs = load_documents()

    if not docs:
        print("Error: No documents loaded!")
        sys.exit(1)

    print(f"\nTotal pages loaded: {len(docs)}")

    # Split into clauses
    print("\nSplitting into clauses...")
    clauses = clause_based_splitter(docs)
    print(f"Total clauses extracted: {len(clauses)}")

    # Load embedding model
    print(f"\nLoading embedding model ({EMBEDDING_MODEL_SIZE})...")
    embedding_model = load_embedding_model(model_size=EMBEDDING_MODEL_SIZE)

    # Build retriever
    print("\nBuilding hybrid retriever...")
    retriever = ClaimLensRetriever(
        clause_documents=clauses,
        embedding_model=embedding_model,
        index_path=os.path.join(BACKEND_DIR, "faiss_claimlens_index"),
        dense_top_k=DENSE_TOP_K,
        use_reranker=USE_RERANKER
    )

    # Load evaluation queries
    print("\nLoading evaluation queries...")
    evaluation_queries = load_evaluation_queries()

    # Run evaluation
    print("\nRunning evaluation...")
    evaluator = RetrievalEvaluator()
    results = evaluator.evaluate(retriever, evaluation_queries)

    # Display results
    print_results(results)

    print("✓ Evaluation complete")


if __name__ == "__main__":
    main()
