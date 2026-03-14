# backend/app/rag/faiss_retriever.py
"""
FAISS-based retriever for pre-indexed policy documents.
Combines functionality from rag-system/retrieval/retriever.py into backend/app/rag.
"""

from functools import lru_cache
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.rag.embeddings import TitanEmbeddingService
from app.rag.storage.s3_client import S3IndexClient
from app.rag.vectorstore.faiss_store import FaissStore

logger = logging.getLogger(__name__)


class FAISSRetriever:
    """
    Retriever for pre-indexed policy documents using FAISS.

    Handles:
    - Loading FAISS index from local disk or S3
    - Generating query embeddings via Titan
    - Performing similarity search
    - Returning ranked results with metadata
    """

    def __init__(self, root_dir: Optional[Path] = None):
        """
        Initialize FAISS retriever.

        Args:
            root_dir: Root directory for index files (defaults to project root)
        """
        if root_dir is None:
            # Default to backend directory
            root_dir = Path(__file__).resolve().parents[2]

        self.root_dir = root_dir
        rag_index_dir_raw = os.getenv("RAG_INDEX_DIR", "").strip()
        rag_index_dir = Path(rag_index_dir_raw) if rag_index_dir_raw else (
            root_dir / "indexes")
        self.index_path = rag_index_dir / "faiss.index"
        self.metadata_path = rag_index_dir / "metadata.parquet"

        aws_region = os.getenv("AWS_REGION", "ap-south-1")
        bedrock_region = os.getenv("BEDROCK_REGION") or aws_region
        bucket = os.getenv("S3_BUCKET_NAME", "claimlens-faiss-index-1")

        self.embedding_service = TitanEmbeddingService(
            region_name=bedrock_region)
        self.s3_client = S3IndexClient(bucket=bucket, region_name=aws_region)
        self.faiss_store = FaissStore(
            index_path=self.index_path,
            metadata_path=self.metadata_path,
            dimension=1536,
        )

        self._initialized = False
        self._cached_embed_query = lru_cache(maxsize=512)(
            self.embedding_service.embed_text)

    def initialize(self, force_reload: bool = False):
        """
        Initialize the retriever by loading index from disk or S3.

        Args:
            force_reload: Force reloading even if already initialized
        """
        if self._initialized and not force_reload:
            return

        if not self.index_path.exists() or not self.metadata_path.exists():
            try:
                self.s3_client.download_index_bundle(
                    self.index_path, self.metadata_path)
            except Exception as e:
                logger.warning(f"Failed to download index from S3: {e}")

        self.faiss_store.load_if_exists()
        self._initialized = True

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Search for similar clauses.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of search results with metadata
        """
        self.initialize()

        query_embedding = self._cached_embed_query(query)
        distances, indices = self.faiss_store.search(query_embedding, k=k)

        results: List[Dict] = []
        for rank, (distance, idx) in enumerate(zip(distances, indices), start=1):
            if idx < 0:
                continue

            metadata = self.faiss_store.get_metadata_by_id(idx)
            if not metadata:
                continue
            results.append(
                {
                    "rank": rank,
                    "score_l2": float(distance),
                    "insurer": metadata.get("insurer"),
                    "policy_name": metadata.get("policy_name"),
                    "clause_id": metadata.get("clause_id"),
                    "text": metadata.get("text"),
                    "page": metadata.get("page"),
                    "section": metadata.get("section"),
                    "source_pdf": metadata.get("source_pdf"),
                }
            )

        return results

    @property
    def index_size(self) -> int:
        """Return the number of vectors in the index."""
        self.initialize()
        return self.faiss_store.ntotal


# Singleton instance
_retriever_instance: Optional[FAISSRetriever] = None


def get_faiss_retriever(root_dir: Optional[Path] = None) -> FAISSRetriever:
    """
    Get or create the FAISS retriever singleton.

    Args:
        root_dir: Optional root directory for index files

    Returns:
        FAISSRetriever instance
    """
    global _retriever_instance

    if _retriever_instance is None:
        _retriever_instance = FAISSRetriever(root_dir=root_dir)

    return _retriever_instance
