from fastapi import APIRouter, File, Form, Request, UploadFile

from app.jobs.queue import enqueue_task
from app.schemas.policies import PolicyListResponse, PolicyUploadResponse
from app.services.policy_service import policy_service


router = APIRouter()


@router.post("/upload", response_model=PolicyUploadResponse)
async def upload_policy(
    request: Request,
    insurer: str = Form(...),
    policy_name: str = Form(...),
    uin: str = Form(...),
    policy_version_year: int = Form(...),
    file: UploadFile = File(...),
) -> PolicyUploadResponse:
    content = await file.read()
    response = policy_service.create_policy(
        insurer=insurer,
        policy_name=policy_name,
        uin=uin,
        policy_version_year=policy_version_year,
        filename=file.filename or "unknown",
        content=content,
        trace_id=request.state.trace_id,
    )
    try:
        enqueue_task("app.jobs.tasks.index_policy_task", response.policy_id)
    except Exception:
        policy_service.update_indexing_status(response.policy_id, "failed")
        response = response.model_copy(update={"indexing_status": "failed", "total_clauses": 0})
    return response


@router.get("", response_model=PolicyListResponse)
async def list_policies() -> PolicyListResponse:
    return PolicyListResponse(policies=policy_service.list_policies())
