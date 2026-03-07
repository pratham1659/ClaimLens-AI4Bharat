import re
from typing import Dict, Iterable, List


SECTION_SPLIT_PATTERN = re.compile(r"\n\s*(?=\d+(?:\.\d+)*\s+[A-Za-z])")
BULLET_SPLIT_PATTERN = re.compile(r"\n\s*(?=(?:[-•*]|\(?[a-zA-Z]\)|\(?[ivxIVX]+\)))")
PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")
SECTION_HEADER_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Za-z][^\n]{1,80})")


def _split_text_blocks(text: str) -> Iterable[str]:
    section_blocks = SECTION_SPLIT_PATTERN.split(text)

    for section_block in section_blocks:
        section_block = section_block.strip()
        if not section_block:
            continue

        bullet_blocks = BULLET_SPLIT_PATTERN.split(section_block)
        for bullet_block in bullet_blocks:
            bullet_block = bullet_block.strip()
            if not bullet_block:
                continue

            for paragraph in PARAGRAPH_SPLIT_PATTERN.split(bullet_block):
                paragraph = paragraph.strip()
                if paragraph:
                    yield paragraph


def _chunk_by_max_tokens(text: str, max_tokens: int = 500) -> List[str]:
    tokens = text.split()
    if not tokens:
        return []

    chunks: List[str] = []
    start = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(" ".join(tokens[start:end]))
        start = end

    return chunks


def _extract_policy_name(source_pdf: str) -> str:
    name = source_pdf.rsplit(".", 1)[0]
    return name.replace("_", " ").replace("-", " ").strip()


def _extract_section(block: str) -> str:
    match = SECTION_HEADER_PATTERN.match(block)
    if match:
        return match.group(2).strip()
    return "General"


def extract_clauses(pages: List[Dict], insurer: str) -> List[Dict]:
    clauses: List[Dict] = []
    clause_counter = 0

    for page_data in pages:
        page_number = page_data["page"]
        source_pdf = page_data["source_pdf"]
        text = page_data["text"]
        policy_name = _extract_policy_name(source_pdf)

        for block in _split_text_blocks(text):
            section = _extract_section(block)
            chunks = _chunk_by_max_tokens(block, max_tokens=500)
            for chunk in chunks:
                clause_counter += 1
                clauses.append(
                    {
                        "clause_id": f"{source_pdf}-{clause_counter}",
                        "insurer": insurer,
                        "policy_name": policy_name,
                        "section": section,
                        "text": chunk,
                        "page": page_number,
                        "source_pdf": source_pdf,
                    }
                )

    return clauses
