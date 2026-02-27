import re
from typing import List
from langchain_core.documents import Document

def _normalize_section(
    line: str,
    section_prefix_pattern,
    letter_section_pattern,
    roman_section_pattern
) -> str:
    line = line.strip()

    if section_prefix_pattern.match(line):
        line = re.sub(r"^SECTION\s+[A-Z]\s+[-–]\s+", "", line, flags=re.IGNORECASE)
    elif letter_section_pattern.match(line):
        line = re.sub(r"^[A-Z]\.\s+", "", line)
    elif roman_section_pattern.match(line):
        line = re.sub(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+", "", line)

    return line.strip().title()


def _is_valid_heading(title: str) -> bool:
    words = title.strip().split()

    if len(words) == 0 or len(words) > 12:
        return False

    if title.endswith("."):
        return False

    lower_title = title.lower()
    forbidden_tokens = ["hours", "days", "lac", "points", "inr", "%", "rs", "per"]
    if any(token in lower_title for token in forbidden_tokens):
        return False

    capitalized = sum(1 for w in words if w[0].isupper())
    if capitalized / len(words) < 0.5:
        return False

    return True


def _save_clause(
    clause_documents: List[Document],
    clause_lines: List[str],
    base_metadata: dict,
    current_section: str,
    clause_number: str,
    clause_title: str,
    start_page: int,
    bullet_pattern
) -> None:

    clause_text = "\n".join(clause_lines).strip()

    metadata = {
        "source": base_metadata.get("source"),
        "file_name": base_metadata.get("file_name"),
        "insurer": base_metadata.get("insurer"),
        "policy_name": base_metadata.get("policy_name"),
        "uin": base_metadata.get("uin"),
        "policy_id": base_metadata.get("policy_id"),
        "policy_version_year": base_metadata.get("policy_version_year"),
        "document_type": base_metadata.get("document_type"),
        "creation_date": base_metadata.get("creation_date"),
        "total_pages": base_metadata.get("total_pages"),
        "chunk_type": "clause_level",
        "section": current_section,
        "clause_number": clause_number,
        "clause_title": clause_title,
        "start_page": start_page
    }

    lines = clause_text.split("\n")

    bullet_indices = [
        i for i, l in enumerate(lines)
        if bullet_pattern.match(l.strip())
    ]

    if not bullet_indices:
        clause_documents.append(
            Document(page_content=clause_text, metadata=metadata)
        )
        return

    for i, bullet_index in enumerate(bullet_indices):
        start = bullet_index

        end = (
            bullet_indices[i + 1]
            if i + 1 < len(bullet_indices)
            else len(lines)
        )

        bullet_chunk_lines = lines[start:end]

        bullet_chunk = "\n".join(bullet_chunk_lines).strip()

        bullet_metadata = metadata.copy()
        bullet_metadata["chunk_type"] = "clause_bullet_level"

        clause_documents.append(
            Document(page_content=bullet_chunk, metadata=bullet_metadata)
        )


def clause_based_splitter(policy_documents: List[Document]) -> List[Document]:
    """
    Production-grade clause splitter with:

    - Section detection
    - Numbered clause detection
    - TOC filtering
    - Hierarchical bullet-level splitting
    - Bullet enrichment (captures explanation below bullets)
    """

    if not policy_documents:
        raise ValueError("clause_based_splitter received empty policy_documents list.")

    sorted_docs = sorted(
        policy_documents,
        key=lambda doc: doc.metadata.get("page", 0)
    )

    if not sorted_docs:
        raise ValueError("No valid documents found after sorting.")

    full_text_lines = []
    page_map = []

    for doc in sorted_docs:
        page_number = doc.metadata.get("page")
        for line in doc.page_content.splitlines():
            full_text_lines.append(line)
            page_map.append(page_number)

    uppercase_section_pattern = re.compile(r"^[A-Z][A-Z\s\-&]+$")
    letter_section_pattern = re.compile(r"^[A-Z]\.\s+[A-Z][A-Za-z\s\-&]+$")
    roman_section_pattern = re.compile(
        r"^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-Z][A-Za-z\s\-&]+$"
    )
    section_prefix_pattern = re.compile(
        r"^SECTION\s+[A-Z]\s+[-–]\s+[A-Za-z\s\-&]+$",
        re.IGNORECASE
    )

    numbered_heading_pattern = re.compile(r"^(\d+(?:\.\d+)*\.)\s+(.+)$")
    bullet_pattern = re.compile(r"^\s*[•\-]\s+")

    clause_documents: List[Document] = []

    current_section = None
    current_clause_number = None
    current_clause_title = None
    current_clause_lines = []
    current_start_page = None

    base_metadata = sorted_docs[0].metadata.copy()

    for index, raw_line in enumerate(full_text_lines):
        line = raw_line.strip()

        if not line:
            continue

        if (
            uppercase_section_pattern.match(line)
            or letter_section_pattern.match(line)
            or roman_section_pattern.match(line)
            or section_prefix_pattern.match(line)
        ):
            current_section = _normalize_section(
                line,
                section_prefix_pattern,
                letter_section_pattern,
                roman_section_pattern
            )
            continue

        numbered_match = numbered_heading_pattern.match(line)

        if numbered_match:
            candiadate_number = numbered_match.group(1)
            candidate_title = numbered_match.group(2).strip()

            if not _is_valid_heading(candidate_title):
                if current_clause_number is not None:
                    current_clause_lines.append(line)
                continue

            if current_clause_number is not None:
                _save_clause(
                    clause_documents,
                    current_clause_lines,
                    base_metadata,
                    current_section,
                    current_clause_number,
                    current_clause_title,
                    current_start_page,
                    bullet_pattern
                )

            current_clause_number = candiadate_number
            current_clause_title = candidate_title
            current_clause_lines = [line]
            current_start_page = page_map[index]

        else:
            if current_clause_number is not None:
                current_clause_lines.append(line)

    if current_clause_number is not None and current_clause_lines:
        _save_clause(
            clause_documents,
            current_clause_lines,
            base_metadata,
            current_section,
            current_clause_number,
            current_clause_title,
            current_start_page,
            bullet_pattern
        )

    return clause_documents