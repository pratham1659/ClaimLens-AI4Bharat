import os
from typing import List

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document


def load_policy(
    pdf_path: str,
    insurer: str,
    policy_name: str,
    uin: str,
    policy_version_year: int,
    document_type: str = "policy_wording"
) -> List[Document]:
    """
    Load a policy PDF and return page-level Document objects
    with structured metadata.
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at path: {pdf_path}")

    loader = PyMuPDFLoader(pdf_path)
    documents = loader.load()

    total_pages = len(documents)
    policy_documents: List[Document] = []

    for doc in documents:
        page_number = doc.metadata.get("page")
        creation_date = doc.metadata.get("creationdate")

        policy_metadata = {
            "source": pdf_path,
            "file_name": os.path.basename(pdf_path),

            "insurer": insurer,
            "policy_name": policy_name,
            "uin": uin,
            "policy_id": f"{policy_name}_{uin}",

            "policy_version_year": policy_version_year,
            "document_type": document_type,
            "creation_date": creation_date,

            "page": page_number,
            "total_pages": total_pages,
            "chunk_type": "page_level",

            "section": None,
            "subsection": None,
            "clause_title": None
        }

        policy_documents.append(
            Document(
                page_content=doc.page_content,
                metadata=policy_metadata
            )
        )

    return policy_documents