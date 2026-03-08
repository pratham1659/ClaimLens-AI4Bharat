"""
Query Builder for ClaimLens RAG system.

Transforms medical reports, discharge summaries, and claim descriptions
into structured retrieval queries optimized for insurance policy matching.
"""

from typing import Dict, List
import re
from langchain_core.prompts import PromptTemplate


QUERY_BUILDER_PROMPT = """
You convert medical reports, discharge summaries, or claim descriptions
into retrieval queries for health insurance policy documents.

Your goal is to generate a query that helps retrieve relevant policy clauses.

Identify all insurance-relevant concepts in the input.

Examples include (but are not limited to):
- illness or diagnosis
- treatment or medical procedure
- hospitalization details
- accidents or emergencies
- maternity or childbirth
- pre-existing diseases
- waiting periods
- exclusions
- medical expenses or coverage

Do not limit yourself to these examples.

Step 1 — Sentence:
Rewrite the input as ONE clear, neutral natural-language sentence that would
retrieve relevant health insurance policy clauses.

The sentence must remain neutral and should NOT assume whether the treatment
is covered or excluded.

Write the sentence as a descriptive statement rather than a question.

Avoid referring to "the patient".

Prefer terminology commonly used in insurance policies.

Important rules:
- ONE sentence
- no boolean operators
- no identifiers like name, age, hospital

Step 2 — Keywords:
Provide 5–10 keywords derived from the input.

Output format:

Sentence:
<sentence>

Keywords:
<comma separated keywords>

Input:
{user_input}
"""


class ClaimLensQueryBuilder:
    """
    Universal Query Builder for ClaimLens RAG system.

    Transforms medical summaries and claim descriptions into structured
    queries optimized for insurance policy clause retrieval.

    Compatible with any LangChain LLM (mock, local, or Bedrock).
    """

    def __init__(self, llm):
        """
        Initialize with a LangChain LLM instance.

        Args:
            llm: LangChain language model (e.g., ChatBedrock, ChatOpenAI, Mock)
        """
        self.llm = llm

        self.prompt = PromptTemplate(
            input_variables=["user_input"],
            template=QUERY_BUILDER_PROMPT
        )

    def build_query(self, user_input: str) -> Dict:
        """
        Transform medical/claim input into structured retrieval query.

        Returns:
            Dict with keys:
            - "sentence": cleaned, neutral query sentence
            - "keywords": list of insurance-relevant keywords
            - "query": combined sentence + keywords for vector search
        """

        formatted_prompt = self.prompt.format(user_input=user_input)

        response = self.llm.invoke(formatted_prompt)

        output = response.content.strip()

        sentence = ""
        keywords: List[str] = []

        # Robust parsing using regex
        sentence_match = re.search(
            r"sentence\s*:\s*(.+)",
            output,
            re.IGNORECASE
        )

        keywords_match = re.search(
            r"keywords\s*:\s*(.+)",
            output,
            re.IGNORECASE
        )

        if sentence_match:
            sentence = sentence_match.group(1).strip()

        if keywords_match:
            keyword_text = keywords_match.group(1)
            keywords = [k.strip() for k in keyword_text.split(",")]

        # Fallback if parsing fails
        if not sentence:
            sentence = user_input[:500]

        combined_query = f"{sentence} {' '.join(keywords)}".strip()

        return {
            "sentence": sentence,
            "keywords": keywords,
            "query": combined_query
        }
