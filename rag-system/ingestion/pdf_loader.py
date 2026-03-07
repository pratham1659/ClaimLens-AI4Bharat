import asyncio
from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader

from ingestion.clause_splitter import extract_clauses
from ingestion.embedding_service import TitanEmbeddingService
from storage.s3_client import S3IndexClient
from vectorstore.faiss_store import FaissStore


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
    index_path = root_dir / "indexes" / "faiss.index"
    metadata_path = root_dir / "indexes" / "metadata.pkl"

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

    embedding_service = TitanEmbeddingService(region_name="us-east-1")
    texts = [clause["text"] for clause in clauses]
    if use_async:
        embeddings = asyncio.run(embedding_service.embed_batch_async(texts, concurrency=8))
    else:
        embeddings = embedding_service.embed_batch(texts, batch_size=16)

    store = FaissStore(index_path=index_path, metadata_path=metadata_path, dimension=1536)
    store.load_if_exists()
    store.add_clauses(clauses, embeddings)
    store.save_local()

    s3 = S3IndexClient(bucket="claimlens-faiss-index-1", region_name="us-east-1")
    s3.upload_index_bundle(index_path, metadata_path)

    return len(clauses)
