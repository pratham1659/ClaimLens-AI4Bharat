from app.schemas.claims import ClaimAnalyzeResponse
from app.schemas.documents import DocumentStatusResponse
from app.schemas.policies import PolicySummary


class InMemoryStore:
    def __init__(self) -> None:
        self.documents: dict[str, DocumentStatusResponse] = {}
        self.policies: dict[str, PolicySummary] = {}
        self.claims: dict[str, ClaimAnalyzeResponse] = {}


store = InMemoryStore()
