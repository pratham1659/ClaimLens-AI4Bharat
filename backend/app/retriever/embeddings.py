import json
import logging
import os
import time
from typing import List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TitanEmbeddingModel:
    """
    Reusable AWS Bedrock Titan embedding model for FAISS-compatible pipelines.

    Provides:
    - embed_text(text): single text embedding
    - embed_batch(texts): batch embedding for indexing

    Also includes LangChain-style wrappers used by existing FAISS code:
    - embed_query(text)
    - embed_documents(texts)
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "amazon.titan-embed-text-v2:0",
        max_retries: int = 3,
        request_timeout_seconds: int = 30,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
    ):
        if model_id != "amazon.titan-embed-text-v2:0":
            raise ValueError("Only amazon.titan-embed-text-v2:0 is supported")

        self.region_name = region_name
        self.model_id = model_id
        self.max_retries = max_retries
        self.request_timeout_seconds = request_timeout_seconds
        self.embedding_dimension = 1536

        client_kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": region_name,
            "config": Config(
                read_timeout=request_timeout_seconds,
                connect_timeout=10,
                retries={"max_attempts": max_retries, "mode": "standard"},
            ),
        }

        if aws_access_key_id:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            client_kwargs["aws_session_token"] = aws_session_token

        self.client = boto3.client(**client_kwargs)

    def _invoke_embedding_api(self, text: str) -> List[float]:
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({"inputText": text}),
                    contentType="application/json",
                    accept="application/json",
                )

                response_payload = json.loads(response["body"].read())
                embedding = response_payload.get("embedding")

                if not isinstance(embedding, list) or len(embedding) == 0:
                    raise ValueError("Empty or invalid embedding returned by Bedrock")

                if len(embedding) != self.embedding_dimension:
                    raise ValueError(
                        f"Unexpected embedding dimension: {len(embedding)} (expected {self.embedding_dimension})"
                    )

                return [float(value) for value in embedding]

            except (ClientError, BotoCoreError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Titan embedding call failed (attempt %s/%s): %s",
                    attempt,
                    self.max_retries,
                    str(exc),
                )

                if attempt < self.max_retries:
                    backoff_seconds = 2 ** (attempt - 1)
                    time.sleep(backoff_seconds)

        logger.error("Titan embedding failed after %s attempts", self.max_retries)
        raise RuntimeError("Bedrock Titan embedding request failed") from last_error

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for one text and return a Python list."""
        cleaned = (text or "").strip()
        if not cleaned:
            logger.warning("Received empty text for embedding; using whitespace placeholder")
            cleaned = " "
        return self._invoke_embedding_api(cleaned)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts and return list-of-lists."""
        embeddings: List[List[float]] = []
        for index, text in enumerate(texts):
            try:
                embeddings.append(self.embed_text(text))
            except Exception as exc:
                logger.error("Failed embedding for batch item %s: %s", index, str(exc))
                raise
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """LangChain compatibility wrapper for query embedding."""
        return self.embed_text(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """LangChain compatibility wrapper for document embedding."""
        return self.embed_batch(texts)


def load_embedding_model(model_size: str = "base") -> TitanEmbeddingModel:
    """
    Load Titan embedding model for retrieval/indexing.

    The `model_size` argument is kept for backward compatibility with
    existing call sites, but it is not used by Titan.
    """
    _ = model_size

    region_name = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    max_retries = int(os.getenv("BEDROCK_EMBEDDING_MAX_RETRIES", "3"))

    logger.info(
        "Loading Titan embedding model (model_id=%s, region=%s)",
        model_id,
        region_name,
    )

    return TitanEmbeddingModel(
        region_name=region_name,
        model_id=model_id,
        max_retries=max_retries,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )
