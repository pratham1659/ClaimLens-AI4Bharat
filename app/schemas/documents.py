from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    policy = "policy"
    discharge_summary = "discharge_summary"


class DocumentStatusResponse(BaseModel):
    document_id: str
    document_type: DocumentType
    filename: str
    status: str
    content_hash: str
    trace_id: str | None = None
