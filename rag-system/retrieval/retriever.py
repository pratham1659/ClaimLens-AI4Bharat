from functools import lru_cache
import os
from pathlib import Path
from typing import Dict, List

from ingestion.embedding_service import TitanEmbeddingService
from storage.s3_client import S3IndexClient
from vectorstore.faiss_store import FaissStore


class Retriever:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.index_path = root_dir / "indexes" / "faiss.index"
        self.metadata_path = root_dir / "indexes" / "metadata.parquet"

        aws_region = os.getenv("AWS_REGION", "ap-south-1")
        bedrock_region = os.getenv("BEDROCK_REGION") or aws_region
        bucket = os.getenv("S3_BUCKET_NAME", "claimlens-faiss-index-1")

        self.embedding_service = TitanEmbeddingService(region_name=bedrock_region)
        self.s3_client = S3IndexClient(bucket=bucket, region_name=aws_region)
        self.faiss_store = FaissStore(
            index_path=self.index_path,
            metadata_path=self.metadata_path,
            dimension=1536,
        )

        self._initialized = False

        self._cached_embed_query = lru_cache(maxsize=512)(self.embedding_service.embed_text)

    def initialize(self, force_reload: bool = False):
        if self._initialized and not force_reload:
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
