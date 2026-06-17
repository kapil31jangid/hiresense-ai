from fastapi import APIRouter, Depends, status
from typing import Dict, Any

from app.common.schemas import (
    RankingCreate, RankingResponse, RankingCandidatesResponse,
    RankingCandidateResponse, RankingExportResponse
)
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.ranking.service import RankingService

router = APIRouter(prefix="/rankings", tags=["Rankings"])

@router.post("", response_model=RankingResponse, status_code=status.HTTP_201_CREATED)
def create_ranking(data: RankingCreate, current_user=Depends(get_current_user)):
    ranking_data = RankingService.create_ranking(data)
    return RankingResponse(
        request_id=get_request_id(),
        ranking=ranking_data
    )

@router.get("/{ranking_id}", response_model=RankingResponse)
def get_ranking(ranking_id: str, current_user=Depends(get_current_user)):
    ranking_data = RankingService.get_ranking(ranking_id)
    return RankingResponse(
        request_id=get_request_id(),
        ranking=ranking_data
    )

@router.get("/{ranking_id}/candidates", response_model=RankingCandidatesResponse)
def get_ranking_candidates(ranking_id: str, current_user=Depends(get_current_user)):
    items = RankingService.get_ranking_candidates(ranking_id)
    return RankingCandidatesResponse(
        request_id=get_request_id(),
        ranking_id=ranking_id,
        items=items
    )

@router.get("/{ranking_id}/candidates/{candidate_id}", response_model=RankingCandidateResponse)
def get_ranking_candidate_detail(ranking_id: str, candidate_id: str, current_user=Depends(get_current_user)):
    candidate_data = RankingService.get_ranking_candidate_detail(ranking_id, candidate_id)
    return RankingCandidateResponse(
        request_id=get_request_id(),
        ranking_id=ranking_id,
        candidate=candidate_data
    )

@router.get("/{ranking_id}/export/csv", response_model=RankingExportResponse)
def export_ranking_csv(ranking_id: str, current_user=Depends(get_current_user)):
    request_id = get_request_id()
    # The export logic fetches already stored results - NO RECOMPUTATION
    export_data = RankingService.export_ranking_csv(ranking_id, request_id)
    return export_data

@router.post("/{ranking_id}/refresh", response_model=RankingResponse)
def refresh_ranking(ranking_id: str, current_user=Depends(get_current_user)):
    ranking_data = RankingService.refresh_ranking(ranking_id)
    return RankingResponse(
        request_id=get_request_id(),
        ranking=ranking_data
    )
