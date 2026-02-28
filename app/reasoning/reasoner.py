import json
import logging
from typing import List

from langchain_core.documents import Document
from langchain_groq import ChatGroq
from pydantic import ValidationError

from app.reasoning.prompt_templates import (
    format_clauses_for_prompt,
    build_chat_prompt_template,
)

from app.reasoning.output_schema import RAGResponse
from app.reasoning.exceptions import ReasoningValidationError


logger = logging.getLogger(__name__)

class ClaimLensReasoner:
    """
    Responsible for:
    - Building the prompt
    - Invoking the LLM
    - Parsing JSON
    - Validating structured output
    - Verifying citation integrity
    - Retrying on format failure
    """

    def __init__(
        self,
        model_name: str = "openai/gpt-oss-20b",
        temperature: float = 0.0,
        max_retries: int = 2,
    ):
        self.llm = ChatGroq(
            model_name=model_name,
            temperature=temperature,
        )

        self.prompt_template = build_chat_prompt_template()
        self.max_retries = max_retries

    def answer(
        self,
        query: str,
        retrieved_clauses: List[Document],
    ) -> RAGResponse:
        """
        Entry point for reasoning.
        Returns a validated RAGResponse.
        """

        formatted_clauses = format_clauses_for_prompt(retrieved_clauses)

        retrieved_clause_ids = {
            doc.metadata.get("clause_id")
            for doc in retrieved_clauses
            if doc.metadata.get("clause_id") is not None
        }

        last_error = None

        for attempt in range(self.max_retries + 1):

            try:
                messages = self._build_messages(
                    query=query,
                    formatted_clauses=formatted_clauses,
                )

                raw_output = self._generate_response(messages)

                parsed = self._parse_json(raw_output)

                validated = RAGResponse(**parsed)

                for citation in validated.citations:
                    if citation.clause_id not in retrieved_clause_ids:
                        raise ReasoningValidationError(
                            f"LLM returned citation not in retrieved context: "
                            f"{citation.clause_id}"
                        )

                return validated

            except (ValidationError, json.JSONDecodeError, ReasoningValidationError) as e:
                last_error = e

                logger.warning(
                    f"Reasoning attempt {attempt + 1} failed: {str(e)}"
                )

        raise ReasoningValidationError(
            f"LLM output failed after {self.max_retries} retries: {str(last_error)}"
        )

    def _build_messages(self, query: str, formatted_clauses: str):
        """
        Creates structured chat messages using the prompt template.
        """
        return self.prompt_template.format_messages(
            user_query=query,
            formatted_clauses=formatted_clauses,
        )

    def _generate_response(self, messages) -> str:
        """
        Calls the LLM and returns raw text output.
        """
        response = self.llm.invoke(messages)
        return response.content.strip()

    def _parse_json(self, text: str) -> dict:
        """
        Strict JSON parsing.
        Fail-fast behavior.
        """
        return json.loads(text)