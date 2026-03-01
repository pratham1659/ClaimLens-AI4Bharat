# backend/app/llm/bedrock_client.py
"""
LLM client supporting both AWS Bedrock (production) and Mock (local development).
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """Invoke the LLM with a prompt."""
        pass

    @abstractmethod
    async def invoke_with_json_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Invoke LLM expecting JSON output."""
        pass


class MockLLMClient(BaseLLMClient):
    """
    Mock LLM client for local development.
    Returns realistic mock responses without AWS costs.
    """

    def __init__(self):
        logger.info("Initialized MockLLMClient for local development")

    async def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        Return mock response for development.
        """
        logger.info(f"MockLLMClient: Processing prompt ({len(prompt)} chars)")

        # Generate contextual mock response
        response_text = self._generate_mock_response(prompt, system_prompt)

        return {
            "content": response_text,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": len(prompt.split()),
                "output_tokens": len(response_text.split())
            }
        }

    async def invoke_with_json_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Return mock JSON response for development.
        """
        # Check if this is a compliance analysis request
        if "compliance" in prompt.lower() or "analysis" in prompt.lower():
            return self._generate_mock_analysis_response(prompt)

        # Check if this is a medical extraction request
        if "medical" in prompt.lower() or "extraction" in prompt.lower():
            return self._generate_mock_medical_extraction(prompt)

        # Default JSON response
        return {
            "status": "success",
            "message": "Mock response generated for development",
            "data": {}
        }

    def _generate_mock_response(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Generate contextual mock response."""
        prompt_lower = prompt.lower()

        if "coverage" in prompt_lower or "policy" in prompt_lower:
            return (
                "Based on the policy terms, the treatment appears to be covered. "
                "The hospitalization expenses fall within the sum insured limit. "
                "However, please verify the waiting period requirements for any "
                "pre-existing conditions. The claim should be filed within 30 days "
                "of discharge for timely processing."
            )

        if "claim" in prompt_lower:
            return (
                "The claim has been reviewed against the policy terms. "
                "The medical procedures performed are generally covered under "
                "the hospitalization benefit. Room rent is within the 1% daily limit. "
                "Recommend approval with standard documentation verification."
            )

        return (
            "This is a mock response generated for local development. "
            "In production, this would be processed by AWS Bedrock Claude. "
            "The mock response simulates realistic AI analysis behavior."
        )

    def _generate_mock_analysis_response(self, prompt: str) -> Dict[str, Any]:
        """Generate mock compliance analysis response."""
        return {
            "approval_score": 78.5,
            "approval_likelihood": "high",
            "compliance_risks": [
                {
                    "risk": "Room rent exceeds standard limit",
                    "severity": "low",
                    "mitigation": "Verify actual room category against policy terms"
                },
                {
                    "risk": "Pre-existing condition waiting period",
                    "severity": "medium",
                    "mitigation": "Confirm policy inception date and condition history"
                }
            ],
            "clause_references": [
                {
                    "clause_id": "HC-001",
                    "content": "Hospitalization coverage up to sum insured",
                    "relevance": "high"
                },
                {
                    "clause_id": "RM-002",
                    "content": "Room rent limited to 1% of sum insured per day",
                    "relevance": "high"
                },
                {
                    "clause_id": "PE-003",
                    "content": "Pre-existing conditions covered after 2 year waiting period",
                    "relevance": "medium"
                }
            ],
            "missing_documentation": [
                "Pre-authorization form (if applicable)",
                "Previous medical records for pre-existing conditions"
            ],
            "recommendations": [
                "Verify room category matches policy entitlement",
                "Confirm treatment dates fall within policy period",
                "Check if any procedures require pre-authorization"
            ],
            "reasoning": (
                "The claim demonstrates good alignment with policy coverage terms. "
                "The primary diagnosis and treatment procedures are standard covered benefits. "
                "Minor concerns exist around room rent limits and pre-existing condition verification. "
                "With proper documentation, this claim has a high likelihood of approval."
            )
        }

    def _generate_mock_medical_extraction(self, prompt: str) -> Dict[str, Any]:
        """Generate mock medical extraction response."""
        return {
            "patient_info": {
                "name": "Test Patient",
                "age": 45,
                "gender": "Male"
            },
            "diagnoses": [
                {
                    "description": "Acute Appendicitis",
                    "icd_code": "K35.80",
                    "is_primary": True
                }
            ],
            "procedures": [
                {
                    "description": "Laparoscopic Appendectomy",
                    "cpt_code": "44970",
                    "date": "2024-01-15"
                }
            ],
            "medications": [
                {"name": "Ceftriaxone", "dosage": "1g IV"},
                {"name": "Metronidazole", "dosage": "500mg IV"}
            ],
            "admission_date": "2024-01-14",
            "discharge_date": "2024-01-16",
            "hospital_name": "Test Medical Center",
            "attending_physician": "Dr. Test Physician"
        }


class BedrockClient(BaseLLMClient):
    """
    Client for AWS Bedrock Claude models (production).
    """

    def __init__(self):
        import boto3
        from botocore.exceptions import ClientError

        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.model_id = settings.BEDROCK_MODEL_ID
        logger.info(f"Initialized BedrockClient with model: {self.model_id}")

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
        from botocore.exceptions import ClientError

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


# Singleton instance
_llm_client_instance: Optional[BaseLLMClient] = None


def get_llm_client(force_mode: Optional[str] = None) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client.

    Automatically selects:
    - MockLLMClient: When USE_MOCK_LLM=true or BEDROCK_ENABLED=false
    - BedrockClient: When BEDROCK_ENABLED=true (production)

    Args:
        force_mode: Force a specific mode ('mock', 'bedrock')

    Returns:
        LLM client instance
    """
    global _llm_client_instance

    if _llm_client_instance is not None and force_mode is None:
        return _llm_client_instance

    # Determine mode
    if force_mode == "mock":
        use_mock = True
    elif force_mode == "bedrock":
        use_mock = False
    else:
        use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
        bedrock_enabled = os.getenv(
            "BEDROCK_ENABLED", "true").lower() == "true"
        use_mock = use_mock or not bedrock_enabled

    if use_mock:
        logger.info("Using MockLLMClient for local development")
        _llm_client_instance = MockLLMClient()
    else:
        logger.info("Using BedrockClient for production")
        _llm_client_instance = BedrockClient()

    return _llm_client_instance
