from fastapi import APIRouter, HTTPException, Request

from app.schemas.claims import ClaimAnalyzeRequest, ClaimAnalyzeResponse
from app.services.claim_service import claim_service


router = APIRouter()


@router.post("/analyze", response_model=ClaimAnalyzeResponse)
async def analyze_claim(request: Request, payload: ClaimAnalyzeRequest) -> ClaimAnalyzeResponse:
    return claim_service.analyze(payload=payload, trace_id=request.state.trace_id)


@router.get("/{claim_id}", response_model=ClaimAnalyzeResponse)
async def get_claim(claim_id: str) -> ClaimAnalyzeResponse:
    claim = claim_service.get_claim(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim
