from fastapi import APIRouter, Depends, status

from app.common.schemas import AIExplanationRequest, AIExplanationResponse
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.ai.service import AIService

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/explanations", response_model=AIExplanationResponse)
def generate_explanation(data: AIExplanationRequest, current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AIService.generate_explanation(data, request_id)
