#!/usr/bin/env python3
"""
ClaimLens RAG Pipeline Runner

Runs full RAG pipeline:
- Load PDF
- Clause split
- Build retriever
- Run reasoning
- Display structured answer

Environment Variables:
    DATA_DIR: Path to data folder (default: ./data)
    INDEX_DIR: Path to FAISS indexes (default: ./indexes)
    EMBEDDING_MODEL_SIZE: small/base/large (default: base)
    DENSE_TOP_K: Dense retrieval candidates (default: 40)
    USE_RERANKER: true/false (default: true)
"""

import os
import sys
import warnings
import logging
from pathlib import Path


os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="huggingface_hub"
)

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)


from dotenv import load_dotenv
from app.rag_main.ingestion.loader import load_policy_documents
from app.rag_main.ingestion.clause_splitter import health_policy_splitter
from app.rag_main.retrieval.embeddings import load_embedding_model
from app.rag_main.retrieval.retriever import ClaimLensRetriever
from app.rag_main.reasoning.reasoner import ClaimLensReasoner
from app.rag_main.pipeline import ClaimLensPipeline

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise EnvironmentError("GROQ_API_KEY not found in environment.")


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
INDEX_DIR = Path(os.environ.get("INDEX_DIR", BASE_DIR / "indexes"))
INDEX_DIR.mkdir(exist_ok=True)

EMBEDDING_MODEL_SIZE = os.environ.get("EMBEDDING_MODEL_SIZE", "base")
DENSE_TOP_K = int(os.environ.get("DENSE_TOP_K", "40"))
USE_RERANKER = os.environ.get("USE_RERANKER", "true").lower() == "true"


def print_banner():
    print("\n" + "=" * 50)
    print("        CLAIMLENS RAG PIPELINE")
    print("=" * 50)
    print(f"Model Size:    {EMBEDDING_MODEL_SIZE}")
    print(f"Dense Top-K:   {DENSE_TOP_K}")
    print(f"Use Reranker:  {USE_RERANKER}")
    print("=" * 50 + "\n")


def main():

    print_banner()

    pdf_path = DATA_DIR / "icici_complete_health.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print("[1] Loading policy document...")
    docs = load_policy_documents(
        pdf_path=str(pdf_path),
        insurer="ICICI Lombard",
        policy_name="Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2024,
    )
    print(f"    ✓ {len(docs)} pages loaded\n")

    print("[2] Splitting into clauses...")
    clauses = health_policy_splitter(docs)
    print(f"    ✓ {len(clauses)} clauses extracted\n")

    print("[3] Loading embedding model...")
    embedding_model = load_embedding_model(
        model_size=EMBEDDING_MODEL_SIZE
    )
    print("    ✓ Embedding model ready\n")

    print("[4] Building retriever...")
    retriever = ClaimLensRetriever(
        clause_documents=clauses,
        embedding_model=embedding_model,
        index_path=str(INDEX_DIR / "icici_faiss"),
        dense_top_k=DENSE_TOP_K,
        use_reranker=USE_RERANKER,
    )
    print("    ✓ Retriever ready\n")

    print("[5] Initializing reasoning engine...")
    reasoner = ClaimLensReasoner()
    print("    ✓ Reasoner ready\n")

    print("[6] Building pipeline...")
    pipeline = ClaimLensPipeline(
        retriever=retriever,
        reasoner=reasoner,
        top_k=5,
    )
    print("    ✓ Pipeline ready\n")

    query = "Is maternity covered?"

    print("[7] Running query...\n")

    response = pipeline.invoke(query)

    print("=" * 50)
    print("RESULT")
    print("=" * 50)
    print("\nQuery:")
    print(query)

    print("\nAnswer:")
    print(response.answer)

    print("\nFound:", response.found)

    print("\nCitations:")
    for citation in response.citations:
        print(f"  - {citation.clause_id} (page {citation.start_page})")

    print("\nConfidence:", response.confidence)
    print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()