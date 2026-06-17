from fastapi import APIRouter, Depends, status

from app.common.schemas import (
    SemanticSearchRequest, SemanticSearchResponse,
    SemanticJobSearchRequest, SemanticJobSearchResponse,
    EmbeddingsRefreshRequest, EmbeddingsRefreshResponse,
    IndexesRebuildRequest, IndexesRebuildResponse,
    IndexesStatusResponse
)
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.semantic_search.service import SemanticSearchService

router = APIRouter(prefix="/semantic-search", tags=["Semantic Search"])

@router.post("/candidates/search", response_model=SemanticSearchResponse)
def search_candidates(data: SemanticSearchRequest, current_user=Depends(get_current_user)):
    items = SemanticSearchService.search_candidates(data)
    return SemanticSearchResponse(
        request_id=get_request_id(),
        job_id=data.job_id,
        items=items
    )

@router.post("/jobs/search", response_model=SemanticJobSearchResponse)
def search_jobs(data: SemanticJobSearchRequest, current_user=Depends(get_current_user)):
    items = SemanticSearchService.search_jobs(data)
    return SemanticJobSearchResponse(
        request_id=get_request_id(),
        candidate_id=data.candidate_id,
        items=items
    )

@router.post("/embeddings/refresh", response_model=EmbeddingsRefreshResponse)
def refresh_embeddings(data: EmbeddingsRefreshRequest, current_user=Depends(get_current_user)):
    refreshed_count = SemanticSearchService.refresh_embeddings(
        entity_type=data.entity_type,
        entity_id=data.entity_id
    )
    return EmbeddingsRefreshResponse(
        request_id=get_request_id(),
        status="COMPLETED",
        refreshed_count=refreshed_count
    )

@router.post("/indexes/rebuild", response_model=IndexesRebuildResponse)
def rebuild_indexes(data: IndexesRebuildRequest, current_user=Depends(get_current_user)):
    rebuilt_indexes = SemanticSearchService.rebuild_indexes(entity_type=data.entity_type)
    return IndexesRebuildResponse(
        request_id=get_request_id(),
        status="COMPLETED",
        rebuilt_indexes=rebuilt_indexes
    )

@router.get("/indexes/status", response_model=IndexesStatusResponse)
def get_indexes_status(current_user=Depends(get_current_user)):
    status_data = SemanticSearchService.get_indexes_status()
    return IndexesStatusResponse(
        request_id=get_request_id(),
        indexes=status_data
    )
