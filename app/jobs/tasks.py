from app.services.document_service import document_service
from app.services.evaluation_service import evaluation_service
from app.services.policy_service import policy_service


def process_document_task(document_id: str) -> None:
    document_service.process_document(document_id)


def index_policy_task(policy_id: str) -> None:
    policy_service.index_policy(policy_id)


def run_evaluation_task(job_id: str) -> None:
    evaluation_service.process_job(job_id)


def dead_letter_sink_task(payload: dict) -> None:
    _ = payload
