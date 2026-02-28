from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from app.core.settings import get_settings
from app.db.models import ClauseModel, PolicyModel
from app.db.session import db_session
from app.schemas.policies import PolicySummary, PolicyUploadResponse


class PolicyService:
    def create_policy(
        self,
        insurer: str,
        policy_name: str,
        uin: str,
        policy_version_year: int,
        filename: str,
        content: bytes,
        trace_id: str,
    ) -> PolicyUploadResponse:
        settings = get_settings()
        content_hash = sha256(content).hexdigest()

        with db_session() as session:
            existing = session.query(PolicyModel).filter(PolicyModel.content_hash == content_hash).first()
            if existing:
                return PolicyUploadResponse(
                    policy_id=existing.policy_id,
                    insurer=existing.insurer,
                    policy_name=existing.policy_name,
                    uin=existing.uin,
                    policy_version_year=existing.policy_version_year,
                    indexing_status=existing.indexing_status,
                    total_clauses=existing.total_clauses,
                    trace_id=trace_id,
                )

            policy_id = f"pol_{uuid4().hex[:12]}"
            ext = Path(filename).suffix or ".pdf"
            path = Path(settings.storage_dir) / "policies" / f"{policy_id}{ext}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

            record = PolicyModel(
                policy_id=policy_id,
                insurer=insurer,
                policy_name=policy_name,
                uin=uin,
                policy_version_year=policy_version_year,
                filename=filename,
                storage_path=str(path),
                content_hash=content_hash,
                indexing_status="in_progress",
                total_clauses=0,
            )
            session.add(record)

            return PolicyUploadResponse(
                policy_id=policy_id,
                insurer=insurer,
                policy_name=policy_name,
                uin=uin,
                policy_version_year=policy_version_year,
                indexing_status="in_progress",
                total_clauses=0,
                trace_id=trace_id,
            )

    def list_policies(self) -> list[PolicySummary]:
        with db_session() as session:
            rows = session.query(PolicyModel).order_by(PolicyModel.created_at.desc()).all()
            return [
                PolicySummary(
                    policy_id=row.policy_id,
                    insurer=row.insurer,
                    policy_name=row.policy_name,
                    uin=row.uin,
                    policy_version_year=row.policy_version_year,
                    indexing_status=row.indexing_status,
                    total_clauses=row.total_clauses,
                )
                for row in rows
            ]

    def index_policy(self, policy_id: str) -> None:
        settings = get_settings()

        with db_session() as session:
            policy = session.get(PolicyModel, policy_id)
            if policy is None:
                return
            policy.indexing_status = "indexing"
            storage_path = policy.storage_path
            insurer = policy.insurer
            policy_name = policy.policy_name
            uin = policy.uin
            policy_version_year = policy.policy_version_year

        try:
            from app.ingestion.clause_splitter import clause_based_splitter
            from app.ingestion.loader import load_policy_documents
            from app.retriever.embeddings import load_embedding_model
            from app.retriever.retriever import ClaimLensRetriever

            docs = load_policy_documents(
                pdf_path=storage_path,
                insurer=insurer,
                policy_name=policy_name,
                uin=uin,
                policy_version_year=policy_version_year,
            )
            clauses = clause_based_splitter(docs)

            with db_session() as session:
                session.query(ClauseModel).filter(ClauseModel.policy_id == policy_id).delete()
                for clause in clauses:
                    session.add(
                        ClauseModel(
                            policy_id=policy_id,
                            clause_id=clause.metadata.get("clause_id"),
                            insurer=clause.metadata.get("insurer"),
                            section=clause.metadata.get("section"),
                            clause_number=clause.metadata.get("clause_number"),
                            clause_title=clause.metadata.get("clause_title"),
                            start_page=clause.metadata.get("start_page"),
                            chunk_type=clause.metadata.get("chunk_type"),
                            content=clause.page_content,
                        )
                    )

            index_path = Path(settings.faiss_index_root) / policy_id
            if index_path.exists():
                rmtree(index_path)

            embedding_model = load_embedding_model("base")
            ClaimLensRetriever(
                clause_documents=clauses,
                embedding_model=embedding_model,
                index_path=str(index_path),
                dense_top_k=40,
                use_reranker=False,
            )

            with db_session() as session:
                policy = session.get(PolicyModel, policy_id)
                if policy is not None:
                    policy.indexing_status = "active"
                    policy.total_clauses = len(clauses)
        except Exception:
            with db_session() as session:
                policy = session.get(PolicyModel, policy_id)
                if policy is not None:
                    policy.indexing_status = "failed"
                    policy.total_clauses = 0

    def update_indexing_status(self, policy_id: str, status: str) -> None:
        with db_session() as session:
            policy = session.get(PolicyModel, policy_id)
            if policy is None:
                return
            policy.indexing_status = status
            if status != "active":
                policy.total_clauses = 0


policy_service = PolicyService()
