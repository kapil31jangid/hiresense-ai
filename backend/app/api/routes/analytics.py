from fastapi import APIRouter, Depends

from app.common.schemas import (
    AnalyticsResponse,
    CandidateFunnelResponse,
    HiringInsightsResponse,
    RankingQualityResponse,
    SkillDistributionResponse,
)
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=AnalyticsResponse)
def get_dashboard_summary(current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AnalyticsService.get_dashboard_summary(request_id)

@router.get("/ranking-quality", response_model=RankingQualityResponse)
def get_ranking_quality(current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AnalyticsService.get_ranking_quality(request_id)

@router.get("/skill-distribution", response_model=SkillDistributionResponse)
def get_skill_distribution(current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AnalyticsService.get_skill_distribution(request_id)

@router.get("/candidate-funnel", response_model=CandidateFunnelResponse)
def get_candidate_funnel(current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AnalyticsService.get_candidate_funnel(request_id)

@router.get("/hiring-insights", response_model=HiringInsightsResponse)
def get_hiring_insights(current_user=Depends(get_current_user)):
    request_id = get_request_id()
    return AnalyticsService.get_hiring_insights(request_id)
