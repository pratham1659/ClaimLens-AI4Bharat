# backend/app/rag/embeddings.py
"""
Embedding generation using AWS Bedrock Titan.
"""

import logging
from typing import List
import boto3
import json
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using AWS Bedrock Titan.
    """

    def __init__(self):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.model_id = settings.BEDROCK_EMBEDDING_MODEL_ID
        self.embedding_dimension = 1536  # Titan embedding dimension

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            # Prepare request body
            body = json.dumps({
                "inputText": text[:8000]  # Titan max input length
            })

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())
            embedding = response_body.get("embedding", [])

            if not embedding:
                raise AIServiceError("Empty embedding returned from Bedrock")

            return embedding

        except ClientError as e:
            logger.error(f"Bedrock embedding error: {str(e)}")
            raise AIServiceError(f"Embedding generation failed: {str(e)}")

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
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            for text in batch:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)

        return embeddings
