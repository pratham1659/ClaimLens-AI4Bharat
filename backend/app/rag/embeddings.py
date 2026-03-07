# backend/app/rag/embeddings.py
"""
Unified embedding generation for semantic retrieval.
Selects local or Bedrock-backed providers based on environment configuration.
"""

import os
import logging
from typing import List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding services."""

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
        self._model = None
        self._model_size = model_size
        self.embedding_dimension = 768  # BGE base dimension

    def _get_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            from app.retriever.embeddings import load_embedding_model
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
        from app.core.config import settings
        from app.retriever.embeddings import TitanEmbeddingModel

        self.model = TitanEmbeddingModel(
            region_name=settings.AWS_REGION,
            model_id=settings.BEDROCK_EMBEDDING_MODEL_ID,
            max_retries=int(os.getenv("BEDROCK_EMBEDDING_MAX_RETRIES", "3")),
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.model_id = settings.BEDROCK_EMBEDDING_MODEL_ID
        self.embedding_dimension = 1536

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
                batch_embeddings = self.model.embed_batch([text[:8000] for text in batch])
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
        if self._mode == "mock":
            logger.info("Initializing MockEmbeddingService for testing")
            self._service = MockEmbeddingService()
        elif self._mode == "local":
            logger.info(
                "Initializing LocalEmbeddingService for local development")
            model_size = os.getenv("EMBEDDING_MODEL_SIZE", "base")
            self._service = LocalEmbeddingService(model_size=model_size)
        else:
            logger.info("Initializing BedrockEmbeddingService for production")
            self._service = BedrockEmbeddingService()

    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension for the current service."""
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
