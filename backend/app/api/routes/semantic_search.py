from fastapi import APIRouter, Depends, status

from app.common.schemas import SemanticSearchRequest, SemanticSearchResponse
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
