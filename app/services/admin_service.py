import json

from app.db.models import DeadLetterModel
from app.db.session import db_session
from app.jobs.queue import enqueue_task
from app.schemas.admin import DeadLetterItem, DeadLetterListResponse, DeadLetterRedriveResponse


class AdminService:
    def list_dead_letters(self, limit: int = 50, offset: int = 0) -> DeadLetterListResponse:
        with db_session() as session:
            total = session.query(DeadLetterModel).count()
            rows = (
                session.query(DeadLetterModel)
                .order_by(DeadLetterModel.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            items = [
                DeadLetterItem(
                    id=row.id,
                    rq_job_id=row.rq_job_id,
                    task_name=row.task_name,
                    origin_queue=row.origin_queue,
                    error_type=row.error_type,
                    error_message=row.error_message,
                    moved_to_queue=row.moved_to_queue,
                    created_at=row.created_at,
                )
                for row in rows
            ]
            return DeadLetterListResponse(items=items, total=total)

    def redrive_dead_letter(self, dead_letter_id: int) -> DeadLetterRedriveResponse:
        with db_session() as session:
            row = session.get(DeadLetterModel, dead_letter_id)
            if row is None:
                return DeadLetterRedriveResponse(
                    dead_letter_id=dead_letter_id,
                    status="not_found",
                    message="Dead letter not found.",
                )

            payload = json.loads(row.payload_json)
            task_name = payload.get("task_name")
            args = payload.get("args", [])
            kwargs = payload.get("kwargs", {})

        if not task_name:
            return DeadLetterRedriveResponse(
                dead_letter_id=dead_letter_id,
                status="failed",
                message="Invalid dead letter payload: missing task name.",
            )

        try:
            new_job_id = enqueue_task(task_name, *args, **kwargs)
        except Exception as exc:
            return DeadLetterRedriveResponse(
                dead_letter_id=dead_letter_id,
                status="failed",
                message=f"Re-drive failed: {exc}",
            )

        with db_session() as session:
            row = session.get(DeadLetterModel, dead_letter_id)
            if row is not None:
                session.delete(row)

        return DeadLetterRedriveResponse(
            dead_letter_id=dead_letter_id,
            status="requeued",
            new_job_id=new_job_id,
            message="Dead letter re-driven to default queue.",
        )


admin_service = AdminService()
