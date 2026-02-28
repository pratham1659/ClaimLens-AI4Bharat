from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.core.settings import get_settings
from app.db.models import DocumentModel
from app.db.session import db_session
from app.schemas.documents import DocumentStatusResponse, DocumentType


class DocumentService:
    def create_document(
        self,
        filename: str,
        document_type: DocumentType,
        content: bytes,
        trace_id: str,
    ) -> DocumentStatusResponse:
        settings = get_settings()
        content_hash = sha256(content).hexdigest()

        with db_session() as session:
            existing = session.query(DocumentModel).filter(DocumentModel.content_hash == content_hash).first()
            if existing:
                existing.trace_id = trace_id
                return DocumentStatusResponse(
                    document_id=existing.document_id,
                    document_type=DocumentType(existing.document_type),
                    filename=existing.filename,
                    status=existing.status,
                    content_hash=existing.content_hash,
                    trace_id=trace_id,
                )

            document_id = f"doc_{uuid4().hex[:12]}"
            ext = Path(filename).suffix or ".pdf"
            path = Path(settings.storage_dir) / "documents" / f"{document_id}{ext}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

            record = DocumentModel(
                document_id=document_id,
                document_type=document_type.value,
                filename=filename,
                storage_path=str(path),
                content_hash=content_hash,
                status="queued",
                trace_id=trace_id,
            )
            session.add(record)

            return DocumentStatusResponse(
                document_id=document_id,
                document_type=document_type,
                filename=filename,
                status="queued",
                content_hash=content_hash,
                trace_id=trace_id,
            )

    def get_document(self, document_id: str) -> DocumentStatusResponse | None:
        with db_session() as session:
            record = session.get(DocumentModel, document_id)
            if record is None:
                return None
            return DocumentStatusResponse(
                document_id=record.document_id,
                document_type=DocumentType(record.document_type),
                filename=record.filename,
                status=record.status,
                content_hash=record.content_hash,
                trace_id=record.trace_id,
            )

    def process_document(self, document_id: str) -> None:
        with db_session() as session:
            record = session.get(DocumentModel, document_id)
            if record is None:
                return
            record.status = "processed"

    def update_status(self, document_id: str, status: str) -> None:
        with db_session() as session:
            record = session.get(DocumentModel, document_id)
            if record is None:
                return
            record.status = status


document_service = DocumentService()
