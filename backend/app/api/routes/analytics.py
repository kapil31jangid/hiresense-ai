from fastapi import APIRouter, Depends

from app.common.schemas import AnalyticsResponse
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=AnalyticsResponse)
def get_dashboard_summary(current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AnalyticsService.get_dashboard_summary(request_id)
