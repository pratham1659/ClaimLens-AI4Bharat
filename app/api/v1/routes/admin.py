from fastapi import APIRouter, HTTPException, Query

from app.schemas.admin import DeadLetterListResponse, DeadLetterRedriveResponse
from app.services.admin_service import admin_service


router = APIRouter()


@router.get("/dead-letters", response_model=DeadLetterListResponse)
async def list_dead_letters(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DeadLetterListResponse:
    return admin_service.list_dead_letters(limit=limit, offset=offset)


@router.post("/dead-letters/{dead_letter_id}/redrive", response_model=DeadLetterRedriveResponse)
async def redrive_dead_letter(dead_letter_id: int) -> DeadLetterRedriveResponse:
    response = admin_service.redrive_dead_letter(dead_letter_id)
    if response.status == "not_found":
        raise HTTPException(status_code=404, detail="Dead letter not found")
    if response.status == "failed":
        raise HTTPException(status_code=500, detail=response.message or "Failed to re-drive dead letter")
    return response
