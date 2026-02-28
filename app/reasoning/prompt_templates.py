# reasoning/prompt_templates.py

from typing import List
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """
You are ClaimLens, a deterministic insurance policy reasoning engine.

You must answer strictly using ONLY the provided policy clauses.

CRITICAL RULES:

1. Use only the provided clauses.
2. Do NOT use external knowledge.
3. Do NOT assume missing information.
4. If the answer is not explicitly supported, return:
   "Answer not found in provided policy context."
5. Every factual claim must be supported by at least one citation.
6. Maximum 3 citations allowed.
7. Never invent or modify clause IDs.
8. If no supporting clause exists:
   - "found": false
   - "citations": []
   - "confidence": "low"
9. Output MUST be valid JSON only.
10. Do NOT include explanations, markdown, or commentary outside JSON.

You are not a conversational assistant.
You are a grounded legal reasoning engine.
""".strip()

def format_clauses_for_prompt(clauses: List[Document]) -> str:
    """
    Converts retrieved Document objects into structured
    context blocks for LLM grounding.
    """

    formatted_blocks = []

    for clause in clauses:
        clause_id = clause.metadata.get("clause_id")
        start_page = clause.metadata.get("start_page")
        content = clause.page_content.strip()

        block = (
            f"[Clause ID: {clause_id} | Page: {start_page}]\n"
            f"{content}"
        )

        formatted_blocks.append(block)

    return "\n\n".join(formatted_blocks)


def build_chat_prompt_template() -> ChatPromptTemplate:
    """
    Returns a reusable ChatPromptTemplate.
    Variables expected:
        - user_query
        - formatted_clauses
    """

    human_template = """
        ### Policy Clauses:

        {formatted_clauses}

        ---

        ### Question:
        {user_query}

        ---

        Respond ONLY in this JSON format:

        {{
        "answer": "string",
        "found": true or false,
        "citations": [
            {{
            "clause_id": "string",
            "start_page": integer
            }}
        ],
        "confidence": "high | medium | low"
        }}

        Important:

        - Maximum 3 citations.
        - Citations must match provided Clause IDs exactly.
        - If not found:
        {{
            "answer": "Answer not found in provided policy context.",
            "found": false,
            "citations": [],
            "confidence": "low"
        }}

        Do not output anything outside JSON.
    """.strip()

    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", human_template),
        ]
    )