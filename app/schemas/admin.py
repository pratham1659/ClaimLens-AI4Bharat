from datetime import datetime

from pydantic import BaseModel


class DeadLetterItem(BaseModel):
    id: int
    rq_job_id: str
    task_name: str
    origin_queue: str
    error_type: str | None = None
    error_message: str | None = None
    moved_to_queue: str
    created_at: datetime


class DeadLetterListResponse(BaseModel):
    items: list[DeadLetterItem]
    total: int


class DeadLetterRedriveResponse(BaseModel):
    dead_letter_id: int
    status: str
    new_job_id: str | None = None
    message: str | None = None
