from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.jobs.queue import enqueue_task
from app.schemas.documents import DocumentStatusResponse, DocumentType
from app.services.document_service import document_service


router = APIRouter()


@router.post("/upload", response_model=DocumentStatusResponse)
async def upload_document(
    request: Request,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
) -> DocumentStatusResponse:
    content = await file.read()
    result = document_service.create_document(
        filename=file.filename or "unknown",
        document_type=document_type,
        content=content,
        trace_id=request.state.trace_id,
    )
    try:
        enqueue_task("app.jobs.tasks.process_document_task", result.document_id)
    except Exception:
        document_service.update_status(result.document_id, "failed")
        result = result.model_copy(update={"status": "failed"})
    return result


@router.get("/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str) -> DocumentStatusResponse:
    document = document_service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
