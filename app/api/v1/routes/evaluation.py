from fastapi import APIRouter, HTTPException, Request

from app.schemas.evaluation import EvaluationJobStatusResponse, EvaluationRunRequest, EvaluationRunResponse
from app.services.evaluation_service import evaluation_service


router = APIRouter()


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    request: Request,
    payload: EvaluationRunRequest,
) -> EvaluationRunResponse:
    return evaluation_service.run(payload=payload, trace_id=request.state.trace_id)


@router.get("/jobs/{job_id}", response_model=EvaluationJobStatusResponse)
async def get_evaluation_job(job_id: str) -> EvaluationJobStatusResponse:
    job = evaluation_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Evaluation job not found")
    return job
