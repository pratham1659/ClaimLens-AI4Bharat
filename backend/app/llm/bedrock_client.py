# backend/app/llm/bedrock_client.py
"""
LLM client supporting AWS Bedrock (production), Ollama (local AI), and Mock (local development).
"""

import os
import logging
import json
import httpx
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
        Invoke LLM expecting JSON output - delegates to invoke and parses JSON.
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

    def _generate_mock_response(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Generate contextual mock response - returns JSON string for analysis requests."""
        prompt_lower = prompt.lower()

        # For compliance/analysis requests, return JSON formatted response
        if "compliance" in prompt_lower or "analysis" in prompt_lower:
            return json.dumps({
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
            }, indent=2)

        # For medical extraction requests, return JSON formatted response
        if "medical" in prompt_lower or "extraction" in prompt_lower:
            return json.dumps({
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
            }, indent=2)

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


class OllamaClient(BaseLLMClient):
    """
    Client for local Ollama server - real AI responses without AWS costs.
    """

    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        logger.info(
            f"Initialized OllamaClient with host: {self.host}, model: {self.model}")

    async def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        Invoke Ollama model with a prompt.

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
            url = f"{self.host}/api/generate"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

            return {
                "content": result.get("response", ""),
                "stop_reason": "stop" if result.get("done") else "length",
                "usage": {
                    "input_tokens": result.get("prompt_eval_count", 0),
                    "output_tokens": result.get("eval_count", 0)
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {str(e)}")
            raise AIServiceError(f"Ollama invocation failed: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Ollama connection error: {str(e)}")
            raise AIServiceError(
                f"Failed to connect to Ollama: {str(e)}. Make sure Ollama is running.")
        except Exception as e:
            logger.error(f"Ollama error: {str(e)}")
            raise AIServiceError(f"Ollama invocation failed: {str(e)}")

    async def invoke_with_json_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Invoke model expecting JSON output.
        """
        # Add JSON instruction to the prompt
        json_prompt = prompt + \
            "\n\nIMPORTANT: Respond with valid JSON only. No additional text or explanation."

        if system_prompt:
            system_prompt = system_prompt + "\n\nYou must respond with valid JSON only."
        else:
            system_prompt = "You must respond with valid JSON only."

        response = await self.invoke(
            prompt=json_prompt,
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


def _check_ollama_available() -> bool:
    """Check if Ollama server is running and available."""
    import httpx

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{ollama_host}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def get_llm_client(force_mode: Optional[str] = None) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client.

    Priority order:
    1. force_mode parameter (if specified)
    2. USE_MOCK_LLM=true (explicit mock mode for UI testing)
    3. BEDROCK_ENABLED=true (production AWS)
    4. OLLAMA_ENABLED=true OR auto-detect Ollama (local AI, real responses)
    5. MockLLMClient as last resort

    By default, tries to use Ollama for real AI responses if available.

    Args:
        force_mode: Force a specific mode ('mock', 'ollama', 'bedrock')

    Returns:
        LLM client instance
    """
    global _llm_client_instance

    if _llm_client_instance is not None and force_mode is None:
        return _llm_client_instance

    # Check environment variables
    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
    bedrock_enabled = os.getenv("BEDROCK_ENABLED", "false").lower() == "true"

    # Determine which client to use
    if force_mode == "mock":
        logger.info("Using MockLLMClient (forced)")
        _llm_client_instance = MockLLMClient()
    elif force_mode == "ollama":
        logger.info("Using OllamaClient (forced)")
        _llm_client_instance = OllamaClient()
    elif force_mode == "bedrock":
        logger.info("Using BedrockClient (forced)")
        _llm_client_instance = BedrockClient()
    elif use_mock:
        logger.info("Using MockLLMClient for UI testing (USE_MOCK_LLM=true)")
        _llm_client_instance = MockLLMClient()
    elif bedrock_enabled:
        logger.info("Using BedrockClient for production (BEDROCK_ENABLED=true)")
        _llm_client_instance = BedrockClient()
    elif ollama_enabled:
        logger.info("Using OllamaClient for local AI (OLLAMA_ENABLED=true)")
        _llm_client_instance = OllamaClient()
    else:
        # Auto-detect: try Ollama first for real AI responses
        logger.info("Auto-detecting LLM backend...")
        if _check_ollama_available():
            logger.info(
                "Ollama detected and available - using OllamaClient for real AI responses")
            _llm_client_instance = OllamaClient()
        else:
            logger.warning(
                "No LLM backend configured and Ollama not available. "
                "Using MockLLMClient. For real AI responses, either:\n"
                "  1. Start Ollama: 'ollama serve' and 'ollama pull llama3.2:3b'\n"
                "  2. Set OLLAMA_ENABLED=true with Ollama running\n"
                "  3. Set BEDROCK_ENABLED=true with AWS credentials"
            )
            _llm_client_instance = MockLLMClient()

    return _llm_client_instance
