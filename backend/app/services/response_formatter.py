"""Response formatter utilities for policy-grounded chatbot replies."""

from __future__ import annotations

import re
from typing import List, Optional, Set


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
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(" ,;:")

    sentence_endings = [idx for idx, ch in enumerate(cleaned) if ch in ".!?"]
    if sentence_endings:
        first_sentence = cleaned[: sentence_endings[0] + 1].strip()
        if len(first_sentence) >= 35:
            return first_sentence

    return ""


def _query_terms(query: str) -> Set[str]:
    stopwords = {
        "the", "is", "are", "does", "can", "will", "what", "when", "where", "how", "this", "that",
        "under", "with", "for", "and", "policy", "cover", "covered", "coverage", "about", "during",
        "into", "from", "your", "their", "have", "been", "would", "could", "should",
    }
    normalized = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in (query or ""))
    return {term for term in normalized.split() if len(term) > 2 and term not in stopwords}


def _is_noise_clause(clause: str) -> bool:
    lowered = clause.lower()
    noise_patterns = [
        "hereinafter",
        "proposer",
        "standard general terms",
        "annexure",
        "page",
        "company limited",
        "policy schedule",
        "this policy is based",
    ]
    if any(pattern in lowered for pattern in noise_patterns):
        return True

    if len(clause.strip()) < 40:
        return True

    if not any(p in clause for p in ".!?"):
        return True

    return False


def _select_relevant_clauses(query: str, clauses: List[str]) -> List[str]:
    terms = _query_terms(query)
    if not clauses:
        return []

    scored = []
    for clause in clauses:
        cleaned = " ".join((clause or "").split()).strip()
        if not cleaned or _is_noise_clause(cleaned):
            continue
        lowered = cleaned.lower()
        overlap = sum(1 for term in terms if term in lowered)
        scored.append((overlap, cleaned))

    scored.sort(key=lambda item: item[0], reverse=True)

    if not scored:
        return []

    min_overlap = 1 if len(terms) <= 4 else 2
    selected = [text for overlap, text in scored if overlap >= min_overlap][:1]
    return selected


def format_acknowledgement(query: str) -> str:
    normalized = (query or "").strip().lower()
    if normalized.startswith(("does", "is", "are", "can", "will", "if")):
        return "That is an important question, and I can help interpret how this policy wording applies."
    return "I understand what you are checking, and I reviewed the relevant policy wording for your question."


def format_policy_reference(query: str, clauses: List[str]) -> str:
    relevant_clauses = _select_relevant_clauses(query, clauses)
    if not relevant_clauses:
        return ""

    summarized = []
    for clause in relevant_clauses[:2]:
        snippet = _summarize_clause(clause)
        if snippet:
            summarized.append(f'- "{snippet}"')

    if not summarized:
        return ""

    return "Relevant policy wording:\n" + "\n".join(summarized)


def format_interpretation(text: str) -> str:
    sentence = _ensure_sentence(text)
    if not sentence:
        sentence = (
            "This should be interpreted along with the policy schedule, limits, exclusions, and applicable waiting periods."
        )
    return f"In simple terms, {sentence[0].lower() + sentence[1:] if len(sentence) > 1 else sentence.lower()}"


def format_key_conditions(query: str, clauses: List[str]) -> str:
    relevant_clauses = _select_relevant_clauses(query, clauses)
    if not relevant_clauses:
        relevant_clauses = [
            " ".join((clause or "").split()).strip()
            for clause in clauses[:1]
            if " ".join((clause or "").split()).strip()
        ]

    if not relevant_clauses:
        return ""

    joined = "\n".join(relevant_clauses).lower()
    if not joined.strip():
        return ""

    conditions: List[str] = []

    day_matches = re.findall(r"\b\d{1,3}\s*days?\b", joined)
    if day_matches:
        unique_days = []
        for value in day_matches:
            normalized = " ".join(value.split())
            if normalized not in unique_days:
                unique_days.append(normalized)
        conditions.append(f"timelines mentioned: {', '.join(unique_days[:3])}")

    month_matches = re.findall(r"\b\d{1,3}\s*months?\b", joined)
    if month_matches:
        unique_months = []
        for value in month_matches:
            normalized = " ".join(value.split())
            if normalized not in unique_months:
                unique_months.append(normalized)
        conditions.append(f"duration windows mentioned: {', '.join(unique_months[:3])}")

    amount_matches = re.findall(r"(?:rs\.?|inr|₹)\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*\s*(?:lakhs?|lacs?|crores?)\b", joined)
    if amount_matches:
        unique_amounts = []
        for value in amount_matches:
            normalized = " ".join(value.split())
            if normalized not in unique_amounts:
                unique_amounts.append(normalized)
        conditions.append(f"monetary limits referenced: {', '.join(unique_amounts[:3])}")

    keyword_map = {
        "waiting period applies": ["waiting period", "pre-existing", "pre existing"],
        "exclusions are referenced": ["excluded", "not covered", "not payable", "exclusion"],
        "cashless/network hospital conditions are referenced": ["cashless", "network hospital"],
    }
    for label, tokens in keyword_map.items():
        if any(token in joined for token in tokens):
            conditions.append(label)

    if not conditions:
        return ""

    formatted_conditions = "\n".join(
        f"- {item[:1].upper() + item[1:] if item else item}"
        for item in conditions[:4]
    )
    return "Key conditions visible in retrieved clauses:\n" + formatted_conditions


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
    explanation = _ensure_sentence(coverage_explanation)
    interpretation = format_interpretation(plain_language_interpretation)
    policy_reference = format_policy_reference(query, clauses)
    key_conditions = format_key_conditions(query, clauses)
    followup_text = _ensure_sentence(follow_up) if follow_up else ""

    sections = [
        explanation,
        interpretation,
        policy_reference,
        key_conditions,
        followup_text,
    ]
    return "\n\n".join([section for section in sections if section])
