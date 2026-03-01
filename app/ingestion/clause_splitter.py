import re
from typing import List
from collections import defaultdict
from langchain_core.documents import Document


def generate_clause_id(insurer, page, identifier, occurrence_index):
    insurer_clean = (insurer or "").replace(" ", "")
    identifier_clean = re.sub(r"\s+", "_", identifier.strip())
    return f"{insurer_clean}_p{page}_{identifier_clean}_{occurrence_index}"


def health_policy_splitter(policy_documents: List[Document]) -> List[Document]:

    if not policy_documents:
        raise ValueError("Empty policy_documents list.")

    # Sort by page order
    sorted_docs = sorted(policy_documents, key=lambda d: d.metadata.get("page", 0))

    noise_patterns = [
        re.compile(r"^UIN\s*:", re.IGNORECASE),
        re.compile(r"^CIN\s*:", re.IGNORECASE),
        re.compile(r"^Page\s+\d+", re.IGNORECASE),
    ]

    numbered_pattern = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)$")
    alpha_pattern = re.compile(r"^([A-Z])\.\s+(.+)$")
    roman_pattern = re.compile(r"^([ivxlcdm]+)\.\s+(.+)$", re.IGNORECASE)
    code_pattern = re.compile(r"^(Code-\s*[A-Za-z]*\d+)\s*:\s*(.+)$")
    definition_pattern = re.compile(
        r"^([A-Z][A-Za-z\s\-\/]+?)\s+means\s+",
        re.IGNORECASE
    )

    clause_documents: List[Document] = []
    clause_counter = defaultdict(int)

    current_identifier = None
    current_lines = []
    current_page = None
    current_metadata = None

    def save_chunk():
        nonlocal current_identifier, current_lines
        nonlocal current_page, current_metadata

        if not current_identifier or not current_lines:
            return

        text = "\n".join(current_lines).strip()
        if not text:
            return

        key = (
            current_metadata.get("insurer"),
            current_page,
            current_identifier,
        )

        clause_counter[key] += 1

        clause_id = generate_clause_id(
            current_metadata.get("insurer"),
            current_page,
            current_identifier,
            clause_counter[key]
        )

        metadata = {
            **current_metadata,
            "chunk_type": "atomic_clause",
            "clause_identifier": current_identifier,
            "clause_id": clause_id,
            "start_page": current_page,
        }

        clause_documents.append(
            Document(page_content=text, metadata=metadata)
        )

    for doc in sorted_docs:

        page_number = doc.metadata.get("page")
        metadata = doc.metadata

        for raw_line in doc.page_content.splitlines():

            line = raw_line.strip()
            if not line:
                continue

            if any(p.match(line) for p in noise_patterns):
                continue

            match = numbered_pattern.match(line)
            if match:
                save_chunk()
                current_identifier = match.group(1)
                current_lines = [line]
                current_page = page_number
                current_metadata = metadata
                continue

            match = alpha_pattern.match(line)
            if match:
                save_chunk()
                current_identifier = match.group(1)
                current_lines = [line]
                current_page = page_number
                current_metadata = metadata
                continue

            match = roman_pattern.match(line)
            if match:
                save_chunk()
                current_identifier = match.group(1)
                current_lines = [line]
                current_page = page_number
                current_metadata = metadata
                continue

            match = code_pattern.match(line)
            if match:
                save_chunk()
                current_identifier = match.group(1)
                current_lines = [line]
                current_page = page_number
                current_metadata = metadata
                continue

            match = definition_pattern.match(line)
            if match:
                save_chunk()
                current_identifier = match.group(1).strip()
                current_lines = [line]
                current_page = page_number
                current_metadata = metadata
                continue

            if current_identifier:
                current_lines.append(line)

    save_chunk()

    ids = [doc.metadata["clause_id"] for doc in clause_documents]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate clause_id detected.")

    return clause_documents