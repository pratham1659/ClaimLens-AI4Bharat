import re
from typing import List
from langchain_core.documents import Document


def clause_based_splitter(policy_documents: List[Document]) -> List[Document]:

    """
    Fully integrated clause splitter with:

    - Robust section detection (multi-pattern, normalized)
    - Section persistence across clauses
    - Numbered clause detection (1, 1.1, 1.1.1)
    - Structural TOC filtering
    - Clean clause-level metadata
    """
    
    if not policy_documents:
        raise ValueError("clause_based_splitter received empty policy_documents list.")

    sorted_docs = sorted(
        policy_documents,
        key=lambda doc: doc.metadata.get("page", 0)
    )

    if not sorted_docs:
        raise ValueError("No valid documents found after sorting. Check loader output.")

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

    clause_documents: List[Document] = []

    current_section = None
    current_clause_number = None
    current_clause_title = None
    current_clause_lines = []
    current_start_page = None

    base_metadata = sorted_docs[0].metadata.copy()

    def normalize_section(line: str) -> str:
        line = line.strip()

        if section_prefix_pattern.match(line):
            line = re.sub(
                r"^SECTION\s+[A-Z]\s+[-–]\s+",
                "",
                line,
                flags=re.IGNORECASE
            )
        elif letter_section_pattern.match(line):
            line = re.sub(r"^[A-Z]\.\s+", "", line)
        elif roman_section_pattern.match(line):
            line = re.sub(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+", "", line)

        return line.strip().title()
    
    def is_valid_heading(title: str) -> bool:
        words = title.strip().split()

        if len(words) == 0 or len(words) > 12:
            return False
        
        sentence_starters = (
        "the ", "if ", "in case ", "further ",
        "however ", "where ", "provided ",
        "subject to "
        )

        lower_title = title.lower()
        if any(lower_title.startswith(starter) for starter in sentence_starters):
            return False
        
        if title.endswith("."):
            return False
        
        forbidden_tokens = ["hours", "days", "lac", "points", "inr", "%", "rs", "per"]
        if any(token in lower_title for token in forbidden_tokens):
            return False
        
        capitalized = sum(1 for w in words if w[0].isupper())
        if capitalized / len(words) < 0.5:
            return False

        return True

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
            current_section = normalize_section(line)
            continue

        numbered_match = numbered_heading_pattern.match(line)

        if numbered_match:

            clause_number = numbered_match.group(1)
            clause_title = numbered_match.group(2).strip()

            if not is_valid_heading(clause_title):
                if current_clause_number is not None:
                    current_clause_lines.append(line)
                continue

            if current_clause_number is not None:

                clause_text = "\n".join(current_clause_lines).strip()

                is_dotted_toc = re.search(
                    r"\.{3,}\s*\d+\s*$",
                    clause_text
                ) is not None

                is_trailing_page_number = re.search(
                    r"^(\d+(?:\.\d+)*)\s+.*\s+\d+$",
                    clause_text
                ) is not None

                has_no_body = len(current_clause_lines) == 1

                if not (is_dotted_toc or is_trailing_page_number or has_no_body):

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
                        "clause_number": current_clause_number,
                        "clause_title": current_clause_title,
                        "start_page": current_start_page
                    }

                    clause_documents.append(
                        Document(
                            page_content=clause_text,
                            metadata=metadata
                        )
                    )

            current_clause_number = numbered_match.group(1)
            current_clause_title = numbered_match.group(2).strip()
            current_clause_lines = [line]
            current_start_page = page_map[index]

        else:
            if current_clause_number is not None:
                current_clause_lines.append(line)

    if current_clause_number is not None and current_clause_lines:

        clause_text = "\n".join(current_clause_lines).strip()

        is_dotted_toc = re.search(
            r"\.{3,}\s*\d+\s*$",
            clause_text
        ) is not None

        is_trailing_page_number = re.search(
            r"^(\d+(?:\.\d+)*)\s+.*\s+\d+$",
            clause_text
        ) is not None

        has_no_body = len(current_clause_lines) == 1

        if not (is_dotted_toc or is_trailing_page_number or has_no_body):

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
                "clause_number": current_clause_number,
                "clause_title": current_clause_title,
                "start_page": current_start_page
            }

            clause_documents.append(
                Document(
                    page_content=clause_text,
                    metadata=metadata
                )
            )

    return clause_documents