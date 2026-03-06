import asyncio
import json
import logging
import time
from typing import List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class TitanEmbeddingService:
    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "amazon.titan-embed-text-v1",
        max_retries: int = 3,
    ):
        self.region_name = region_name
        self.model_id = model_id
        self.max_retries = max_retries
        self.embedding_dimension = 1536

        self.bedrock = boto3.client("bedrock-runtime", region_name=region_name)

    def _invoke_with_retry(self, text: str) -> List[float]:
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
                    raise ValueError("Bedrock response missing valid embedding list")

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

        raise RuntimeError("Titan embedding failed after retries") from last_error

    def embed_text(self, text: str) -> List[float]:
        clean_text = (text or "").strip() or " "
        return self._invoke_with_retry(clean_text)

    def embed_batch(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                embeddings.append(self.embed_text(text))
        return embeddings

    async def embed_batch_async(self, texts: List[str], concurrency: int = 8) -> List[List[float]]:
        semaphore = asyncio.Semaphore(concurrency)

        async def _one(text: str) -> List[float]:
            async with semaphore:
                return await asyncio.to_thread(self.embed_text, text)

        tasks = [_one(text) for text in texts]
        return await asyncio.gather(*tasks)
