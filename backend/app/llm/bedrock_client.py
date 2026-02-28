# backend/app/llm/bedrock_client.py
"""
AWS Bedrock client for LLM interactions.
"""

import logging
import json
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)


class BedrockClient:
    """
    Client for AWS Bedrock Claude models.
    """

    def __init__(self):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.model_id = settings.BEDROCK_MODEL_ID

    async def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        Invoke Claude model with a prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            top_p: Top-p sampling parameter

        Returns:
            Model response
        """
        try:
            # Build messages
            messages = [
                {"role": "user", "content": prompt}
            ]

            # Build request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "messages": messages
            }

            if system_prompt:
                body["system"] = system_prompt

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())

            return {
                "content": response_body.get("content", [{}])[0].get("text", ""),
                "stop_reason": response_body.get("stop_reason"),
                "usage": response_body.get("usage", {})
            }

        except ClientError as e:
            logger.error(f"Bedrock invocation error: {str(e)}")
            raise AIServiceError(f"LLM invocation failed: {str(e)}")

    async def invoke_with_json_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Invoke model expecting JSON output.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_tokens: Maximum tokens

        Returns:
            Parsed JSON response
        """
        response = await self.invoke(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.0  # Lower temperature for structured output
        )

        content = response["content"]

        # Extract JSON from response
        try:
            # Try to find JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)

            # Try parsing entire content as JSON
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.debug(f"Raw response: {content}")
            raise AIServiceError(f"Invalid JSON response from LLM: {str(e)}")
