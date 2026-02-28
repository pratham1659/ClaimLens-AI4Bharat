import json
from datetime import datetime, timezone

from redis import Redis
from rq import Queue, Retry
from rq.job import Job

from app.core.settings import get_settings
from app.db.models import DeadLetterModel, DocumentModel, JobModel, PolicyModel
from app.db.session import db_session


def _parse_retry_intervals(raw: str) -> list[int]:
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return [int(item) for item in items]


def _build_retry() -> Retry:
    settings = get_settings()
    intervals = _parse_retry_intervals(settings.rq_retry_intervals)
    return Retry(max=settings.rq_retry_max, interval=intervals)


def _dead_letter_on_failure(job: Job, connection, *exc_info) -> None:
    settings = get_settings()

    retries_left = getattr(job, "retries_left", None)
    if retries_left not in (None, 0):
        return

    if job.meta.get("dead_lettered"):
        return

    error_type = None
    error_message = None
    traceback_text = None
    if len(exc_info) >= 3:
        exc_type, exc_value, tb = exc_info[0], exc_info[1], exc_info[2]
        error_type = getattr(exc_type, "__name__", str(exc_type))
        error_message = str(exc_value) if exc_value is not None else None
        traceback_text = "".join(tb) if isinstance(tb, list) else str(tb)

    payload = {
        "rq_job_id": job.id,
        "task_name": job.func_name,
        "args": job.args,
        "kwargs": job.kwargs,
        "origin_queue": job.origin,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error_type": error_type,
        "error_message": error_message,
    }

    dlq = Queue(settings.rq_dead_letter_queue, connection=connection)
    dlq.enqueue("app.jobs.tasks.dead_letter_sink_task", payload, retry=None)

    with db_session() as session:
        session.add(
            DeadLetterModel(
                rq_job_id=job.id,
                task_name=job.func_name,
                origin_queue=job.origin,
                payload_json=json.dumps(payload, default=str),
                error_type=error_type,
                error_message=error_message,
                traceback_text=traceback_text,
                moved_to_queue=settings.rq_dead_letter_queue,
            )
        )

        if job.func_name.endswith("process_document_task") and job.args:
            document = session.get(DocumentModel, job.args[0])
            if document is not None:
                document.status = "failed"

        if job.func_name.endswith("index_policy_task") and job.args:
            policy = session.get(PolicyModel, job.args[0])
            if policy is not None:
                policy.indexing_status = "failed"
                policy.total_clauses = 0

        if job.func_name.endswith("run_evaluation_task") and job.args:
            eval_job = session.get(JobModel, job.args[0])
            if eval_job is not None:
                eval_job.status = "failed"
                eval_job.error_message = error_message or "RQ task failed"

    job.meta["dead_lettered"] = True
    job.save_meta()


def get_queue() -> Queue:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    return Queue(settings.rq_default_queue, connection=connection)


def enqueue_task(function_path: str, *args, **kwargs) -> str:
    queue = get_queue()
    job = queue.enqueue(
        function_path,
        *args,
        retry=_build_retry(),
        on_failure=_dead_letter_on_failure,
        **kwargs,
    )
    return job.id
