# backend/app/rag/storage/s3_client.py
"""
S3 client for FAISS index upload/download operations.
Extracted from rag-system/storage/s3_client.py
"""

import logging
import time
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class S3IndexClient:
    """
    S3 client for managing FAISS index storage.

    Handles upload and download of FAISS index bundles (index + metadata)
    with retry logic for reliability.
    """

    def __init__(
        self,
        bucket: str = "claimlens-faiss-index-1",
        region_name: str = "us-east-1",
        max_retries: int = 3,
    ):
        self.bucket = bucket
        self.max_retries = max_retries
        self.s3 = boto3.client("s3", region_name=region_name)

    def ensure_layout(self):
        """Ensure expected key prefixes exist in S3.

        S3 is key-based storage, so these are zero-byte marker objects to keep
        a stable, human-friendly layout in consoles/tools.
        """
        self._retry(
            lambda: self.s3.put_object(Bucket=self.bucket, Key="indexes/"),
            "ensure indexes/ prefix",
        )

    def _retry(self, fn, description: str):
        """Execute function with retry logic."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return fn()
            except (ClientError, BotoCoreError, FileNotFoundError) as exc:
                last_error = exc
                logger.warning(
                    "S3 operation failed (%s) attempt %s/%s: %s",
                    description,
                    attempt,
                    self.max_retries,
                    str(exc),
                )
                if attempt < self.max_retries:
                    time.sleep(2 ** (attempt - 1))

        raise RuntimeError(
            f"S3 operation failed after retries: {description}") from last_error

    def upload_index_bundle(self, faiss_path: Path, metadata_path: Path):
        """
        Upload FAISS index and metadata to S3.

        Args:
            faiss_path: Path to FAISS index file
            metadata_path: Path to metadata parquet file
        """
        self.ensure_layout()
        self._retry(
            lambda: self.s3.upload_file(
                str(faiss_path), self.bucket, "indexes/faiss.index"),
            "upload faiss.index",
        )
        self._retry(
            lambda: self.s3.upload_file(
                str(metadata_path), self.bucket, "indexes/metadata.parquet"),
            "upload metadata.parquet",
        )

    def download_index_bundle(self, faiss_path: Path, metadata_path: Path):
        """
        Download FAISS index and metadata from S3.

        Args:
            faiss_path: Local path to save FAISS index
            metadata_path: Local path to save metadata parquet
        """
        faiss_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        self._retry(
            lambda: self.s3.download_file(
                self.bucket, "indexes/faiss.index", str(faiss_path)),
            "download faiss.index",
        )
        self._retry(
            lambda: self.s3.download_file(
                self.bucket, "indexes/metadata.parquet", str(metadata_path)),
            "download metadata.parquet",
        )
