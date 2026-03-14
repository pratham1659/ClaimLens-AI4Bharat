# backend/app/rag/embeddings.py
"""
Unified embedding generation for semantic retrieval.
Selects local or Bedrock-backed providers based on environment configuration.

Includes:
- TitanEmbeddingService: Direct AWS Bedrock Titan embeddings (for RAG ingestion pipeline)
- TitanEmbeddingModel: LangChain-compatible Titan embeddings (for FAISS retrieval)
- LocalEmbeddingService: HuggingFace/sentence-transformers embeddings
- BedrockEmbeddingService: Production Bedrock wrapper using TitanEmbeddingModel
- MockEmbeddingService: Deterministic mock embeddings for testing
- EmbeddingService: Factory class for automatic selection
"""

import asyncio
import json
import os
import logging
import time
from typing import List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# =============================================================================
# TitanEmbeddingService - Direct Bedrock Titan embedding service
# =============================================================================

class TitanEmbeddingService:
    """
    Direct AWS Bedrock Titan embedding service.
    Used by ingestion pipeline for batch embedding generation.

    Extracted from rag-system/ingestion/embedding_service.py
    """

    def __init__(
        self,
        region_name: Optional[str] = None,
        model_id: Optional[str] = None,
        max_retries: int = 3,
        embedding_dimension: Optional[int] = None,
    ):
        resolved_region = (
            region_name
            or os.getenv("BEDROCK_REGION")
            or os.getenv("AWS_REGION", "us-east-1")
        )
        resolved_model_id = model_id or os.getenv(
            "BEDROCK_EMBEDDING_MODEL_ID",
            "amazon.titan-embed-text-v2:0",
        )

        if resolved_model_id != "amazon.titan-embed-text-v2:0":
            raise ValueError(
                "Only amazon.titan-embed-text-v2:0 is supported for this ingestion pipeline"
            )

        self.region_name = resolved_region
        self.model_id = resolved_model_id
        self.max_retries = max_retries
        self.embedding_dimension = embedding_dimension or int(
            os.getenv("BEDROCK_EMBEDDING_DIMENSION", "1024")
        )

        try:
            import boto3
            self.bedrock = boto3.client(
                "bedrock-runtime", region_name=resolved_region)
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

    def _invoke_with_retry(self, text: str) -> List[float]:
        """Invoke Bedrock with retry logic."""
        from botocore.exceptions import BotoCoreError, ClientError

        last_error: Optional[Exception] = None
        payload = json.dumps({"inputText": text})

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=payload,
                    contentType="application/json",
                    accept="application/json",
                )

                body = json.loads(response["body"].read())
                embedding = body.get("embedding")
                if not isinstance(embedding, list):
                    raise ValueError(
                        "Bedrock response missing valid embedding list")

                if len(embedding) != self.embedding_dimension:
                    raise ValueError(
                        f"Unexpected embedding dimension: {len(embedding)} (expected {self.embedding_dimension})"
                    )

                return [float(x) for x in embedding]

            except (ClientError, BotoCoreError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Titan embed call failed (attempt %s/%s): %s",
                    attempt,
                    self.max_retries,
                    str(exc),
                )
                if attempt < self.max_retries:
                    time.sleep(2 ** (attempt - 1))
            except Exception as exc:
                last_error = exc
                logger.error(f"Unexpected error during embedding: {exc}")
                if attempt < self.max_retries:
                    time.sleep(2 ** (attempt - 1))

        raise RuntimeError(
            "Titan embedding failed after retries") from last_error

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        clean_text = (text or "").strip() or " "
        return self._invoke_with_retry(clean_text)

    def embed_batch(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """Generate embeddings for a batch of texts (sequential)."""
        embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            for text in batch:
                embeddings.append(self.embed_text(text))
        return embeddings

    async def embed_batch_async(self, texts: List[str], concurrency: int = 8) -> List[List[float]]:
        """Generate embeddings for a batch of texts (async with concurrency)."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _one(text: str) -> List[float]:
            async with semaphore:
                return await asyncio.to_thread(self.embed_text, text)

        tasks = [_one(text) for text in texts]
        return await asyncio.gather(*tasks)


# =============================================================================
# TitanEmbeddingModel - LangChain-compatible Titan embedding model
# (Merged from backend/app/retriever/embeddings.py)
# =============================================================================

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
        embedding_dimension: Optional[int] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
    ):
        if model_id != "amazon.titan-embed-text-v2:0":
            raise ValueError(
                "Unsupported Bedrock embedding model "
                f"'{model_id}'. Set BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0"
            )

        self.region_name = region_name
        self.model_id = model_id
        self.max_retries = max_retries
        self.request_timeout_seconds = request_timeout_seconds
        self.embedding_dimension = embedding_dimension or int(
            os.getenv("BEDROCK_EMBEDDING_DIMENSION", "1024")
        )

        try:
            import boto3
            from botocore.config import Config

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
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

    def _invoke_embedding_api(self, text: str) -> List[float]:
        """Invoke Bedrock embedding API with retry logic."""
        from botocore.exceptions import BotoCoreError, ClientError

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
                    raise ValueError(
                        "Empty or invalid embedding returned by Bedrock")

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
            except Exception as exc:
                last_error = exc
                logger.error(f"Unexpected error during embedding: {exc}")
                if attempt < self.max_retries:
                    time.sleep(2 ** (attempt - 1))

        logger.error("Titan embedding failed after %s attempts",
                     self.max_retries)
        raise RuntimeError(
            "Bedrock Titan embedding request failed") from last_error

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for one text and return a Python list."""
        cleaned = (text or "").strip()
        if not cleaned:
            logger.warning(
                "Received empty text for embedding; using whitespace placeholder")
            cleaned = " "
        return self._invoke_embedding_api(cleaned)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts and return list-of-lists."""
        embeddings: List[List[float]] = []
        for index, text in enumerate(texts):
            try:
                embeddings.append(self.embed_text(text))
            except Exception as exc:
                logger.error(
                    "Failed embedding for batch item %s: %s", index, str(exc))
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

    region_name = os.getenv("BEDROCK_REGION") or os.getenv(
        "AWS_REGION", "us-east-1")
    model_id = os.getenv("BEDROCK_EMBEDDING_MODEL_ID",
                         "amazon.titan-embed-text-v2:0")
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
        embedding_dimension=int(
            os.getenv("BEDROCK_EMBEDDING_DIMENSION", "1024")),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


# =============================================================================
# Abstract Base Class
# =============================================================================


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding services."""

    embedding_dimension: int = 768  # Default dimension

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass


class LocalEmbeddingService(BaseEmbeddingService):
    """
    Local embedding service using HuggingFace models.
    Uses sentence-transformers for efficient local inference.
    """

    def __init__(self, model_size: str = "base"):
        self._model: Optional[TitanEmbeddingModel] = None
        self._model_size = model_size
        self.embedding_dimension = 768  # BGE base dimension

    def _get_model(self) -> TitanEmbeddingModel:
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info(
                f"Loading local embedding model (size: {self._model_size})")
            self._model = load_embedding_model(model_size=self._model_size)
        return self._model

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using local HuggingFace model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            model = self._get_model()
            # Truncate text if too long
            text = text[:8000]
            embedding = model.embed_query(text)
            return list(embedding)
        except Exception as e:
            logger.error(f"Local embedding error: {str(e)}")
            raise

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using local model.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch

        Returns:
            List of embedding vectors
        """
        try:
            model = self._get_model()
            # Truncate texts
            texts = [t[:8000] for t in texts]
            embeddings = model.embed_documents(texts)
            return [list(e) for e in embeddings]
        except Exception as e:
            logger.error(f"Local batch embedding error: {str(e)}")
            raise


class BedrockEmbeddingService(BaseEmbeddingService):
    """
    Production embedding service using AWS Bedrock Titan.
    """

    def __init__(self):
        try:
            from app.core.config import settings

            self.model = TitanEmbeddingModel(
                region_name=settings.AWS_REGION,
                model_id=settings.BEDROCK_EMBEDDING_MODEL_ID,
                max_retries=int(
                    os.getenv("BEDROCK_EMBEDDING_MAX_RETRIES", "3")),
                embedding_dimension=settings.BEDROCK_EMBEDDING_DIMENSION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            self.model_id = settings.BEDROCK_EMBEDDING_MODEL_ID
            self.embedding_dimension = settings.BEDROCK_EMBEDDING_DIMENSION
        except Exception as e:
            logger.error(f"Failed to initialize BedrockEmbeddingService: {e}")
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using AWS Bedrock Titan.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            return self.model.embed_text(text[:8000])
        except Exception as e:
            logger.error(f"Bedrock embedding error: {str(e)}")
            raise

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using AWS Bedrock.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                batch_embeddings = self.model.embed_batch(
                    [text[:8000] for text in batch])
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Bedrock batch embedding error: {str(e)}")
                raise

        return embeddings


class MockEmbeddingService(BaseEmbeddingService):
    """
    Mock embedding service for testing without actual model loading.
    Returns deterministic mock embeddings.
    """

    def __init__(self, dimension: int = 768):
        self.embedding_dimension = dimension

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding based on text hash."""
        import hashlib

        # Create deterministic embedding based on text content
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed_value = int(text_hash[:8], 16)

        # Generate pseudo-random but deterministic values
        embedding = []
        for i in range(self.embedding_dimension):
            value = ((seed_value + i * 31) % 1000) / 1000.0 - 0.5
            embedding.append(value)

        return embedding

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """Generate mock embeddings for batch."""
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings


class EmbeddingService:
    """
    Factory class that creates the appropriate embedding service based on environment.

    Automatically selects:
    - LocalEmbeddingService for local semantic embedding generation
    - BedrockEmbeddingService for production semantic embedding generation
    - MockEmbeddingService for deterministic test-only embeddings

    Usage:
        service = EmbeddingService()
        embedding = await service.generate_embedding("some text")
    """

    def __init__(self, force_mode: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            force_mode: Force a specific mode ('local', 'bedrock', 'mock')
        """
        self._service: Optional[BaseEmbeddingService] = None
        self._mode = force_mode or self._detect_mode()
        self._initialize_service()

    def _detect_mode(self) -> str:
        """Detect which embedding mode to use based on environment."""
        # Check for explicit mock mode
        embedding_mode = os.getenv("EMBEDDING_MODE", "").lower()
        if embedding_mode == "mock":
            return "mock"

        # Check if using mock LLM (local development)
        use_mock_llm = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
        bedrock_enabled = os.getenv(
            "BEDROCK_ENABLED", "true").lower() == "true"

        if use_mock_llm or not bedrock_enabled:
            return "local"

        return "bedrock"

    def _initialize_service(self):
        """Initialize the appropriate embedding service."""
        try:
            if self._mode == "mock":
                logger.info("Initializing MockEmbeddingService for testing")
                self._service = MockEmbeddingService()
            elif self._mode == "local":
                logger.info(
                    "Initializing LocalEmbeddingService for local development")
                model_size = os.getenv("EMBEDDING_MODEL_SIZE", "base")
                self._service = LocalEmbeddingService(model_size=model_size)
            else:
                logger.info(
                    "Initializing BedrockEmbeddingService for production")
                self._service = BedrockEmbeddingService()
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            # Fallback to mock service if initialization fails
            logger.info("Falling back to MockEmbeddingService")
            self._service = MockEmbeddingService()
            self._mode = "mock"

    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension for the current service."""
        if self._service is None:
            return 768  # Default dimension
        return self._service.embedding_dimension

    @property
    def mode(self) -> str:
        """Get the current embedding mode."""
        return self._mode

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if self._service is None:
            raise RuntimeError("Embedding service not initialized")
        return await self._service.generate_embedding(text)

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch

        Returns:
            List of embedding vectors
        """
        if self._service is None:
            raise RuntimeError("Embedding service not initialized")
        return await self._service.generate_embeddings_batch(texts, batch_size)


# Singleton instance for convenience
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service(force_mode: Optional[str] = None) -> EmbeddingService:
    """
    Get or create the embedding service singleton.

    Args:
        force_mode: Force a specific mode ('local', 'bedrock', 'mock')

    Returns:
        EmbeddingService instance
    """
    global _embedding_service_instance

    # Forced mode should be request-scoped and must not overwrite the global singleton,
    # otherwise one endpoint (e.g., local/mock fallback) can contaminate all subsequent requests.
    if force_mode is not None:
        return EmbeddingService(force_mode=force_mode)

    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()

    return _embedding_service_instance
