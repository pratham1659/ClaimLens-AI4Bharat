# backend/app/api/v1/endpoints/analysis.py
"""
Analysis endpoints for claim compliance analysis.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, status

from app.schemas.analysis import AnalysisResponse, AnalysisRequest
from app.schemas.common import SingleResponse
from app.models.user import User
from app.services.analysis_service import AnalysisService
from app.api.deps import get_analysis_service, get_current_user
from app.core.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _to_analysis_response(result) -> AnalysisResponse:
    payload = AnalysisResponse.model_validate(result).model_dump()

    raw_response = getattr(result, "raw_response", None) or {}
    debug_info = raw_response.get("debug_info") if isinstance(raw_response, dict) else None
    if debug_info:
        payload["debug_info"] = debug_info

    return AnalysisResponse.model_validate(payload)


@router.post(
    "/analyze",
    response_model=SingleResponse[AnalysisResponse],
    summary="Analyze claim"
)
async def analyze_claim(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Perform AI-powered compliance analysis on a claim.

    This endpoint:
    1. Retrieves relevant policy clauses using RAG
    2. Extracts medical information from discharge summary
    3. Analyzes compliance using Claude AI
    4. Returns detailed analysis with recommendations
    """
    result = await analysis_service.analyze_claim(
        claim_id=request.claim_id,
        user=current_user
    )

    return SingleResponse(
        data=_to_analysis_response(result),
        message="Analysis completed successfully"
    )


@router.get(
    "/claim/{claim_id}",
    response_model=SingleResponse[AnalysisResponse],
    summary="Get analysis result"
)
async def get_analysis(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Get the latest analysis result for a claim.
    """
    result = await analysis_service.get_analysis_result(
        claim_id=claim_id,
        user=current_user
    )

    if not result:
        raise ResourceNotFoundError("Analysis", claim_id)

    return SingleResponse(
        data=_to_analysis_response(result)
    )


@router.get(
    "/claim/{claim_id}/history",
    response_model=list[AnalysisResponse],
    summary="Get analysis history"
)
async def get_analysis_history(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Get all historical analysis results for a claim.
    """
    results = await analysis_service.get_analysis_history(
        claim_id=claim_id,
        user=current_user
    )

    return [_to_analysis_response(r) for r in results]
