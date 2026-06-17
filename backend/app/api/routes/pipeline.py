from fastapi import APIRouter, Depends, status, BackgroundTasks
from typing import Dict, Any

from app.common.schemas import (
    PipelineRunRequest, PipelineRunResponse,
    PipelineRunDetailResponse, PipelineFailuresResponse
)
from app.common.context import get_request_id
from app.api.auth import require_admin
from app.modules.data_pipeline.service import PipelineService

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

@router.post("/runs/ingest", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_ingest(data: PipelineRunRequest, background_tasks: BackgroundTasks, current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.trigger_ingest(data, request_id, background_tasks)

@router.post("/runs/embeddings-refresh", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_embeddings_refresh(data: PipelineRunRequest, background_tasks: BackgroundTasks, current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.trigger_embeddings_refresh(data, request_id, background_tasks)

@router.post("/runs/ranking-sync", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_ranking_sync(data: PipelineRunRequest, background_tasks: BackgroundTasks, current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.trigger_ranking_sync(data, request_id, background_tasks)

@router.post("/runs/analytics-refresh", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_analytics_refresh(data: PipelineRunRequest, background_tasks: BackgroundTasks, current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.trigger_analytics_refresh(data, request_id, background_tasks)

@router.get("/runs/{pipeline_run_id}", response_model=PipelineRunDetailResponse)
def get_pipeline_run(pipeline_run_id: str, current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.get_pipeline_run(pipeline_run_id, request_id)

@router.get("/failures", response_model=PipelineFailuresResponse)
def get_pipeline_failures(current_user=Depends(require_admin)):
    request_id = get_request_id()
    return PipelineService.get_pipeline_failures(request_id)
