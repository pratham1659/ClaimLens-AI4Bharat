from pydantic import BaseModel


class PolicyUploadResponse(BaseModel):
    policy_id: str
    insurer: str
    policy_name: str
    uin: str
    policy_version_year: int
    indexing_status: str
    total_clauses: int = 0
    trace_id: str | None = None


class PolicySummary(BaseModel):
    policy_id: str
    insurer: str
    policy_name: str
    uin: str
    policy_version_year: int
    indexing_status: str
    total_clauses: int = 0


class PolicyListResponse(BaseModel):
    policies: list[PolicySummary]
