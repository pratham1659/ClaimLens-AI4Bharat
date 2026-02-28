from pydantic import BaseModel


class EvaluationRunRequest(BaseModel):
    insurer_scope: str = "both"
    use_reranker: bool = True
    dense_top_k: int = 40


class EvaluationRunResponse(BaseModel):
    status: str
    job_id: str | None = None
    metrics: dict[str, float] | None = None
    trace_id: str | None = None
    message: str | None = None


class EvaluationJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, float] | None = None
    error_message: str | None = None
