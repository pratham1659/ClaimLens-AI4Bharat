import os
import warnings
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="huggingface_hub"
)

import logging
logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

from app.ingestion.loader import load_policy_documents
from app.ingestion.clause_splitter import health_policy_splitter
from app.retrieval.retriever import ClaimLensRetriever
from app.reasoning.reasoner import ClaimLensReasoner
from app.pipeline import ClaimLensPipeline

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise EnvironmentError("GROQ_API_KEY not found in environment.")


def main():

    print("\n========================================")
    print("        CLAIMLENS RAG PIPELINE          ")
    print("========================================\n")

    BASE_DIR = Path(__file__).resolve().parents[1]
    DATA_DIR = BASE_DIR / "data"
    INDEX_DIR = BASE_DIR / "indexes"
    INDEX_DIR.mkdir(exist_ok=True)

    PDF_PATH = DATA_DIR / "icici_complete_health.pdf"

    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found at path: {PDF_PATH}")

    print("[1] Loading policy document...")
    docs = load_policy_documents(
        pdf_path=str(PDF_PATH),
        insurer="ICICI Lombard",
        policy_name="Health Insurance",
        uin="ICIHLIP25035V082425",
        policy_version_year=2024,
    )
    print(f"    ✓ Loaded {len(docs)} page-level documents.\n")

    print("[2] Splitting into clauses...")
    clauses = health_policy_splitter(docs)
    print(f"    ✓ Generated {len(clauses)} clause-level documents.\n")

    print("[3] Initializing embedding model...")
    embedding_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5"
    )
    print("    ✓ Embedding model ready.\n")

    print("[4] Building hybrid retriever (Dense + BM25 + Reranker)...")

    retriever = ClaimLensRetriever(
        clause_documents=clauses,
        embedding_model=embedding_model,
        index_path=str(INDEX_DIR / "icici_faiss"),
        dense_top_k=40,
        use_reranker=True
    )

    print("    ✓ Retriever ready.\n")

    print("[5] Initializing reasoning engine...")
    reasoner = ClaimLensReasoner()
    print("    ✓ Reasoner ready.\n")

    print("[6] Building pipeline...")
    pipeline = ClaimLensPipeline(
        retriever=retriever,
        reasoner=reasoner,
        top_k=5,
    )
    print("    ✓ Pipeline ready.\n")

    query = "Is maternity covered?"

    print("[7] Running query...\n")

    response = pipeline.invoke(query)

    print("========================================")
    print("               RESULT                   ")
    print("========================================\n")

    print("Query:")
    print(query)

    print("\nAnswer:")
    print(response.answer)

    print("\nFound:", response.found)

    print("\nCitations:")
    for citation in response.citations:
        print(f"  - {citation.clause_id} (page {citation.start_page})")

    print("\nConfidence:", response.confidence)

    print("\n========================================\n")


if __name__ == "__main__":
    main()