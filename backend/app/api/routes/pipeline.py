from fastapi import APIRouter, Depends, status

from app.common.schemas import PipelineRunRequest, PipelineRunResponse
from app.common.context import get_request_id
from app.api.auth import require_admin
from app.modules.data_pipeline.service import PipelineService

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

@router.post("/runs/ranking-sync", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_ranking_sync(data: PipelineRunRequest, current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.trigger_ranking_sync(data, request_id)
