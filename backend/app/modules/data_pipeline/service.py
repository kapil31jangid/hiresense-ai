from typing import Dict
from datetime import datetime

from app.common.schemas import PipelineRunRequest, PipelineRunResponse, PipelineStatus
from app.common.errors import HireSenseException
from app.modules.job.service import _jobs_db

_pipeline_runs_db: Dict[str, Dict] = {}
_pipeline_counter = 0

class PipelineService:
    @staticmethod
    def trigger_ranking_sync(data: PipelineRunRequest, request_id: str) -> PipelineRunResponse:
        global _pipeline_counter
        # Validate job_id
        if data.job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {data.job_id} was not found."
            )
            
        # Check if there's already an active running pipeline for this job to prevent concurrent runs
        for run in _pipeline_runs_db.values():
            if run["job_id"] == data.job_id and run["status"] == PipelineStatus.RUNNING:
                raise HireSenseException(
                    status_code=409,
                    code="PIPELINE_ALREADY_RUNNING",
                    message=f"A ranking synchronization pipeline is already running for job {data.job_id}."
                )
                
        _pipeline_counter += 1
        run_id = f"pipe_rank_{_pipeline_counter:03d}"
        
        run_record = {
            "pipeline_run_id": run_id,
            "job_id": data.job_id,
            "trigger_mode": data.trigger_mode,
            "status": PipelineStatus.QUEUED,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        _pipeline_runs_db[run_id] = run_record
        
        return PipelineRunResponse(
            request_id=request_id,
            pipeline_run_id=run_id,
            status=PipelineStatus.QUEUED
        )
