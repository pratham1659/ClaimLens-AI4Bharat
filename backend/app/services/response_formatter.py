"""Response formatter utilities for policy-grounded chatbot replies."""

from __future__ import annotations

from typing import List, Optional


def _ensure_sentence(text: str) -> str:
    cleaned = " ".join((text or "").split()).strip()
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _summarize_clause(clause: str, max_len: int = 260) -> str:
    cleaned = " ".join((clause or "").split()).strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    truncated = cleaned[:max_len].rstrip(" ,;:")
    return f"{truncated}..."


def format_acknowledgement(query: str) -> str:
    normalized = (query or "").strip().lower()
    if normalized.startswith(("does", "is", "are", "can", "will", "if")):
        return "That is an important question, and I can help interpret how this policy wording applies."
    return "I understand what you are checking, and I reviewed the relevant policy wording for your question."


def format_policy_reference(clauses: List[str]) -> str:
    if not clauses:
        return (
            "According to the policy wording I found:\n\n"
            "I could not locate a clearly matching clause in the retrieved policy text for this question."
        )

    summarized = []
    for clause in clauses[:2]:
        snippet = _summarize_clause(clause)
        if snippet:
            summarized.append(f'"{snippet}"')

    if not summarized:
        return (
            "According to the policy wording I found:\n\n"
            "I could not locate a clearly matching clause in the retrieved policy text for this question."
        )

    return "According to the policy wording I found:\n\n" + "\n".join(summarized)


def format_interpretation(text: str) -> str:
    sentence = _ensure_sentence(text)
    if not sentence:
        sentence = (
            "This should be interpreted along with the policy schedule, limits, exclusions, and applicable waiting periods."
        )
    return f"In simple terms, {sentence[0].lower() + sentence[1:] if len(sentence) > 1 else sentence.lower()}"


def format_followup(query: str) -> str:
    normalized = (query or "").lower()
    if any(token in normalized for token in ("liability", "sum insured", "limit", "maximum")):
        return (
            "If you share the Sum Insured and any deductible or sub-limit from your policy schedule, "
            "I can help estimate the likely payable amount more precisely."
        )
    if any(token in normalized for token in ("waiting", "pre", "post", "days")):
        return (
            "If you share the treatment date and hospitalization timeline, I can map these timelines to your policy conditions."
        )
    return (
        "If you would like, share the treatment details and hospitalization context, and I can give you a more precise policy-based interpretation."
    )


def generate_final_response(
    query: str,
    clauses: List[str],
    coverage_explanation: str,
    plain_language_interpretation: str,
    follow_up: Optional[str] = None,
) -> str:
    acknowledgement = format_acknowledgement(query)
    explanation = _ensure_sentence(coverage_explanation)
    policy_reference = format_policy_reference(clauses)
    interpretation = format_interpretation(plain_language_interpretation)
    followup_text = _ensure_sentence(follow_up) if follow_up else _ensure_sentence(format_followup(query))

    sections = [
        acknowledgement,
        explanation,
        policy_reference,
        interpretation,
        followup_text,
    ]
    return "\n\n".join([section for section in sections if section])
