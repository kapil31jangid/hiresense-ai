from fastapi import APIRouter, Depends, status
from typing import Dict, Any

from app.common.schemas import (
    AIExplanationRequest, AIExplanationResponse, AIExplanationsResponse,
    AICompareRequest, AICompareResponse,
    AIShortlistSummaryRequest, AIShortlistSummaryResponse
)
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.ai.service import AIService

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/explanations", response_model=AIExplanationResponse)
def generate_explanation(data: AIExplanationRequest, current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AIService.generate_explanation(data, request_id)

@router.get("/explanations/{ranking_id}", response_model=AIExplanationsResponse)
def get_explanations(ranking_id: str, current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AIService.get_explanations(ranking_id, request_id)

@router.post("/compare", response_model=AICompareResponse)
def compare_candidates(data: AICompareRequest, current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AIService.compare_candidates(data, request_id)

@router.post("/shortlist-summary", response_model=AIShortlistSummaryResponse)
def shortlist_summary(data: AIShortlistSummaryRequest, current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AIService.shortlist_summary(data, request_id)
