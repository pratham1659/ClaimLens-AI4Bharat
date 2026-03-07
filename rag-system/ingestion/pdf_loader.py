import asyncio
import os
import logging
from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader

from ingestion.clause_splitter import extract_clauses
from ingestion.embedding_service import TitanEmbeddingService
from storage.s3_client import S3IndexClient
from vectorstore.faiss_store import FaissStore


logger = logging.getLogger(__name__)


def infer_insurer_from_filename(filename: str) -> str:
    lowered = filename.lower()
    if "icici" in lowered:
        return "ICICI"
    if "niva" in lowered:
        return "Niva Bupa"
    return "Unknown"


def load_pdf_pages(pdf_path: Path) -> List[Dict]:
    reader = PdfReader(str(pdf_path))
    pages: List[Dict] = []

    for page_index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(
                {
                    "page": page_index,
                    "text": text,
                    "source_pdf": pdf_path.name,
                }
            )

    return pages


def load_policy_documents(policies_dir: Path) -> List[Dict]:
    all_pages: List[Dict] = []
    for pdf_path in sorted(policies_dir.glob("*.pdf")):
        all_pages.extend(load_pdf_pages(pdf_path))
    return all_pages


def run_ingestion_pipeline(root_dir: Path, use_async: bool = True) -> int:
    policies_dir = root_dir / "documents" / "policies"
    index_dir_raw = os.getenv("RAG_INDEX_DIR", "").strip()
    index_dir = Path(index_dir_raw) if index_dir_raw else (root_dir / "indexes")
    index_path = index_dir / "faiss.index"
    metadata_path = index_dir / "metadata.parquet"
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    bedrock_region = os.getenv("BEDROCK_REGION") or aws_region
    bucket = os.getenv("S3_BUCKET_NAME", "claimlens-faiss-index-1")

    if not policies_dir.exists():
        return 0

    pages = load_policy_documents(policies_dir)
    clauses: List[Dict] = []

    by_pdf: Dict[str, List[Dict]] = {}
    for page in pages:
        by_pdf.setdefault(page["source_pdf"], []).append(page)

    for source_pdf, source_pages in by_pdf.items():
        insurer = infer_insurer_from_filename(source_pdf)
        clauses.extend(extract_clauses(source_pages, insurer=insurer))

    if not clauses:
        return 0

    embedding_service = TitanEmbeddingService(region_name=bedrock_region)
    texts = [clause["text"] for clause in clauses]
    batch_size = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "16"))
    concurrency = int(os.getenv("RAG_EMBEDDING_CONCURRENCY", "2"))

    if use_async:
        try:
            embeddings = asyncio.run(
                embedding_service.embed_batch_async(texts, concurrency=max(1, concurrency))
            )
        except Exception as async_error:
            logger.warning(
                "Async embedding failed (%s). Falling back to sequential embedding.",
                async_error,
            )
            embeddings = embedding_service.embed_batch(texts, batch_size=max(1, batch_size))
    else:
        embeddings = embedding_service.embed_batch(texts, batch_size=max(1, batch_size))

    store = FaissStore(
        index_path=index_path,
        metadata_path=metadata_path,
        dimension=embedding_service.embedding_dimension,
    )
    store.load_if_exists()
    store.add_clauses(clauses, embeddings)
    try:
        store.save_local()
    except Exception as save_error:
        # Common in mounted volumes where container user cannot write.
        logger.warning(
            "Primary index write failed at %s (%s). Retrying in /tmp/rag-system-indexes",
            index_dir,
            save_error,
        )
        tmp_index_dir = Path("/tmp/rag-system-indexes")
        index_path = tmp_index_dir / "faiss.index"
        metadata_path = tmp_index_dir / "metadata.parquet"

        retry_store = FaissStore(
            index_path=index_path,
            metadata_path=metadata_path,
            dimension=embedding_service.embedding_dimension,
        )
        retry_store.add_clauses(clauses, embeddings)
        retry_store.save_local()

    s3 = S3IndexClient(bucket=bucket, region_name=aws_region)
    s3.upload_index_bundle(index_path, metadata_path)

    return len(clauses)
