import json
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

from app.core.settings import get_settings
from app.db.models import ClauseModel, JobModel
from app.db.session import db_session
from app.evaluation.evaluator import RetrievalEvaluator
from app.jobs.queue import enqueue_task
from app.schemas.evaluation import EvaluationJobStatusResponse, EvaluationRunRequest, EvaluationRunResponse


class EvaluationService:
    def run(self, payload: EvaluationRunRequest, trace_id: str) -> EvaluationRunResponse:
        job_id = f"job_{uuid4().hex[:12]}"
        with db_session() as session:
            session.add(
                JobModel(
                    job_id=job_id,
                    job_type="evaluation",
                    status="queued",
                    payload_json=payload.model_dump_json(),
                    result_json=None,
                    error_message=None,
                    trace_id=trace_id,
                )
            )

        status = "accepted"
        message = "Evaluation job accepted."
        try:
            enqueue_task("app.jobs.tasks.run_evaluation_task", job_id)
        except Exception as exc:
            with db_session() as session:
                job = session.get(JobModel, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = f"Queue enqueue failed: {exc}"
            status = "failed"
            message = "Evaluation job could not be enqueued."

        return EvaluationRunResponse(
            status=status,
            job_id=job_id,
            metrics=None,
            trace_id=trace_id,
            message=message,
        )

    def process_job(self, job_id: str) -> None:
        settings = get_settings()
        with db_session() as session:
            job = session.get(JobModel, job_id)
            if job is None:
                return
            job.status = "running"
            payload = EvaluationRunRequest(**json.loads(job.payload_json))

        try:
            from app.retriever.embeddings import load_embedding_model
            from app.retriever.retriever import ClaimLensRetriever

            with db_session() as session:
                clause_rows = session.query(ClauseModel).all()

            clause_documents = [
                Document(
                    page_content=row.content,
                    metadata={
                        "clause_id": row.clause_id,
                        "insurer": row.insurer,
                        "section": row.section,
                        "clause_number": row.clause_number,
                        "clause_title": row.clause_title,
                        "start_page": row.start_page,
                        "chunk_type": row.chunk_type,
                    },
                )
                for row in clause_rows
            ]

            if not clause_documents:
                raise ValueError("No indexed clauses available for evaluation.")

            eval_path = Path("data") / "evaluation_queries.json"
            with eval_path.open("r", encoding="utf-8") as f:
                evaluation_queries = json.load(f)

            embedding_model = load_embedding_model("base")
            retriever = ClaimLensRetriever(
                clause_documents=clause_documents,
                embedding_model=embedding_model,
                index_path=str(Path(settings.faiss_index_root) / "global_eval"),
                dense_top_k=payload.dense_top_k,
                use_reranker=payload.use_reranker,
            )
            evaluator = RetrievalEvaluator()
            metrics = evaluator.evaluate(retriever, evaluation_queries)

            with db_session() as session:
                job = session.get(JobModel, job_id)
                if job is not None:
                    job.status = "completed"
                    job.result_json = json.dumps(metrics)
                    job.error_message = None
        except Exception as exc:
            with db_session() as session:
                job = session.get(JobModel, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(exc)

    def get_job_status(self, job_id: str) -> EvaluationJobStatusResponse | None:
        with db_session() as session:
            job = session.get(JobModel, job_id)
            if job is None:
                return None
            result = json.loads(job.result_json) if job.result_json else None
            return EvaluationJobStatusResponse(
                job_id=job.job_id,
                status=job.status,
                result=result,
                error_message=job.error_message,
            )


evaluation_service = EvaluationService()
