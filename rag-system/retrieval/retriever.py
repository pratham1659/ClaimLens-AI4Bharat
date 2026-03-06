from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from ingestion.embedding_service import TitanEmbeddingService
from storage.s3_client import S3IndexClient
from vectorstore.faiss_store import FaissStore


class Retriever:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.index_path = root_dir / "indexes" / "faiss.index"
        self.metadata_path = root_dir / "indexes" / "metadata.pkl"

        self.embedding_service = TitanEmbeddingService(region_name="us-east-1")
        self.s3_client = S3IndexClient(bucket="claimlens-faiss-index", region_name="us-east-1")
        self.faiss_store = FaissStore(
            index_path=self.index_path,
            metadata_path=self.metadata_path,
            dimension=1536,
        )

        self._initialized = False

        self._cached_embed_query = lru_cache(maxsize=512)(self.embedding_service.embed_text)

    def initialize(self):
        if self._initialized:
            return

        if not self.index_path.exists() or not self.metadata_path.exists():
            self.s3_client.download_index_bundle(self.index_path, self.metadata_path)

        self.faiss_store.load_if_exists()
        self._initialized = True

    def search(self, query: str, k: int = 5) -> List[Dict]:
        self.initialize()

        query_embedding = self._cached_embed_query(query)
        distances, indices = self.faiss_store.search(query_embedding, k=k)

        results: List[Dict] = []
        for rank, (distance, idx) in enumerate(zip(distances, indices), start=1):
            if idx < 0 or idx >= len(self.faiss_store.metadata):
                continue

            metadata = self.faiss_store.metadata[idx]
            results.append(
                {
                    "rank": rank,
                    "score_l2": float(distance),
                    "insurer": metadata.get("insurer"),
                    "clause_id": metadata.get("clause_id"),
                    "text": metadata.get("text"),
                    "page": metadata.get("page"),
                    "source_pdf": metadata.get("source_pdf"),
                }
            )

        return results
