import re
from typing import List
from collections import defaultdict
from langchain_core.documents import Document


def generate_clause_id(insurer, page, clause_number, occurrence_index):
    insurer_clean = (insurer or "").replace(" ", "")
    clause_clean = clause_number.strip().rstrip(".")
    return f"{insurer_clean}_p{page}_{clause_clean}_{occurrence_index}"

def clause_based_splitter(policy_documents: List[Document]) -> List[Document]:

    if not policy_documents:
        raise ValueError("Empty policy_documents list.")

    sorted_docs = sorted(
        policy_documents,
        key=lambda doc: (
            doc.metadata.get("insurer", ""),
            doc.metadata.get("page", 0),
        )
    )

    numbered_heading_pattern = re.compile(r"^(\d+(?:\.\d+)*\.)\s+(.+)$")
    bullet_pattern = re.compile(r"^\s*[•\-]\s+")

    clause_documents: List[Document] = []
    clause_counter = defaultdict(int)

    current_clause_number = None
    current_clause_lines = []
    current_start_page = None
    current_metadata = None

    def save_clause():
        nonlocal current_clause_number, current_clause_lines
        nonlocal current_start_page, current_metadata

        if not current_clause_number or not current_metadata:
            return

        clause_text = "\n".join(current_clause_lines).strip()

        key = (
            current_metadata.get("insurer"),
            current_start_page,
            current_clause_number,
        )
        clause_counter[key] += 1

        clause_id = generate_clause_id(
            current_metadata.get("insurer"),
            current_start_page,
            current_clause_number,
            clause_counter[key]
        )

        metadata_base = {
            **current_metadata,
            "chunk_type": "clause_level",
            "clause_number": current_clause_number,
            "clause_id": clause_id,
            "start_page": current_start_page
        }

        lines = clause_text.split("\n")

        bullet_indices = [
            i for i, l in enumerate(lines)
            if bullet_pattern.match(l.strip())
        ]

        if not bullet_indices:
            clause_documents.append(
                Document(page_content=clause_text, metadata=metadata_base)
            )
            return

        for i, bullet_index in enumerate(bullet_indices):
            start = bullet_index
            end = (
                bullet_indices[i + 1]
                if i + 1 < len(bullet_indices)
                else len(lines)
            )

            bullet_chunk = "\n".join(lines[start:end]).strip()

            bullet_metadata = metadata_base.copy()
            bullet_metadata["chunk_type"] = "clause_bullet_level"
            bullet_metadata["clause_id"] = f"{clause_id}__b{i+1}"

            clause_documents.append(
                Document(page_content=bullet_chunk, metadata=bullet_metadata)
            )

    for doc in sorted_docs:

        page_number = doc.metadata.get("page")
        doc_metadata = doc.metadata

        for raw_line in doc.page_content.splitlines():

            line = raw_line.strip()
            if not line:
                continue

            match = numbered_heading_pattern.match(line)

            if match:

                if current_clause_number is not None:
                    save_clause()

                current_clause_number = match.group(1)
                current_clause_lines = [line]
                current_start_page = page_number
                current_metadata = doc_metadata

            else:
                if current_clause_number is not None:
                    current_clause_lines.append(line)

    if current_clause_number is not None:
        save_clause()

    ids = [doc.metadata["clause_id"] for doc in clause_documents]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate clause_id detected after splitting.")

    return clause_documents