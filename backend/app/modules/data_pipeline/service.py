from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import BackgroundTasks

from app.common.schemas import (
    PipelineRunRequest, PipelineRunResponse, PipelineStatus,
    PipelineRunDetail, PipelineRunDetailResponse,
    PipelineFailureItem, PipelineFailuresResponse,
    FreshnessStatus
)
from app.common.errors import HireSenseException
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.modules.ranking.service import _rankings_db
from app.modules.analytics.service import AnalyticsService

_pipeline_runs_db: Dict[str, Dict[str, Any]] = {}
_pipeline_failures_db: Dict[str, Dict[str, Any]] = {}

_pipeline_counter = 0
_failure_counter = 0

# Checkpoint: track the last successful run timestamp (UTC)
_last_successful_checkpoint: datetime = datetime(2026, 5, 27, 0, 0, 0)

def _parse_iso(val: str) -> datetime:
    normalized = val.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).replace(tzinfo=None)

def _get_changed_entities(checkpoint: datetime):
    changed_jobs = []
    for j_id, j in _jobs_db.items():
        up_time = _parse_iso(j.get("updated_at", j.get("created_at", "1970-01-01T00:00:00Z")))
        if up_time > checkpoint:
            changed_jobs.append(j_id)
            
    changed_candidates = []
    for c_id, c in _candidates_db.items():
        up_time = _parse_iso(c.get("updated_at", c.get("created_at", "1970-01-01T00:00:00Z")))
        if up_time > checkpoint:
            changed_candidates.append(c_id)
            
    return changed_jobs, changed_candidates

def _run_ingest_step(run_record: Dict[str, Any]):
    job_id = run_record.get("job_id")
    if job_id == "JOB_FAIL_INGEST":
        raise RuntimeError("Ingest step failed.")
    
    global _last_successful_checkpoint
    # Process incrementally
    changed_jobs, changed_candidates = _get_changed_entities(_last_successful_checkpoint)
    run_record["processed_jobs"] = changed_jobs
    run_record["processed_candidates"] = changed_candidates
    
    # Advance the checkpoint only to the latest processed source timestamp.
    # If nothing changed, keep the previous checkpoint so future edits are still discoverable.
    processed_timestamps = []
    for j_id in changed_jobs:
        processed_timestamps.append(
            _parse_iso(_jobs_db[j_id].get("updated_at", _jobs_db[j_id].get("created_at", "1970-01-01T00:00:00Z")))
        )
    for c_id in changed_candidates:
        processed_timestamps.append(
            _parse_iso(_candidates_db[c_id].get("updated_at", _candidates_db[c_id].get("created_at", "1970-01-01T00:00:00Z")))
        )

    if processed_timestamps:
        _last_successful_checkpoint = max(processed_timestamps)

def _run_embeddings_refresh_step(run_record: Dict[str, Any]):
    job_id = run_record.get("job_id")
    if job_id == "JOB_FAIL_EMBEDDING":
        raise RuntimeError("Embedding refresh step failed.")
        
    from app.modules.semantic_search.service import SemanticSearchService
    if job_id:
        SemanticSearchService.refresh_embeddings("JOB", job_id)
    else:
        SemanticSearchService.refresh_embeddings()

def _run_ranking_sync_step(run_record: Dict[str, Any]):
    job_id = run_record.get("job_id")
    if job_id == "JOB_FAIL_RANKING":
        raise RuntimeError("Ranking sync step failed.")
        
    from app.modules.ranking.service import RankingService
    if job_id:
        matching_rankings = [r_id for r_id, r in _rankings_db.items() if r["job_id"] == job_id]
        for r_id in matching_rankings:
            RankingService.refresh_ranking(r_id)
    else:
        changed_jobs, changed_candidates = _get_changed_entities(_last_successful_checkpoint)
        affected_rankings = set()
        for r_id, r in _rankings_db.items():
            if r["job_id"] in changed_jobs:
                affected_rankings.add(r_id)
            else:
                cands_in_run = {c["candidate_id"] for c in r.get("candidates", [])}
                if cands_in_run.intersection(changed_candidates):
                    affected_rankings.add(r_id)
        for r_id in affected_rankings:
            RankingService.refresh_ranking(r_id)

def _run_analytics_refresh_step(run_record: Dict[str, Any]):
    job_id = run_record.get("job_id")
    if job_id == "JOB_FAIL_ANALYTICS":
        raise RuntimeError("Analytics refresh step failed.")
        
    now_str = datetime.utcnow().isoformat() + "Z"
    AnalyticsService.update_freshness(now_str, FreshnessStatus.FRESH)

def _execute_run_with_retries(run_id: str, step_function, source_module: str, failure_stage: str):
    run = _pipeline_runs_db[run_id]
    run["status"] = PipelineStatus.RUNNING
    run["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        run["retry_count"] = attempt - 1
        try:
            step_function(run)
            run["status"] = PipelineStatus.COMPLETED
            run["updated_at"] = datetime.utcnow().isoformat() + "Z"
            return
        except Exception as e:
            run["error_message"] = str(e)
            run["updated_at"] = datetime.utcnow().isoformat() + "Z"
            
            if attempt == max_retries:
                run["status"] = PipelineStatus.FAILED
                
                # Write to pipeline_failures
                global _failure_counter
                _failure_counter += 1
                fail_id = f"fail_{_failure_counter:03d}"
                failure_record = {
                    "failure_id": fail_id,
                    "pipeline_run_id": run_id,
                    "job_id": run.get("job_id"),
                    "source_module": source_module,
                    "failure_stage": failure_stage,
                    "retry_count": max_retries,
                    "error_message": str(e),
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "resolved": False
                }
                _pipeline_failures_db[fail_id] = failure_record

class PipelineService:
    @staticmethod
    def _create_run(data: PipelineRunRequest, run_type_prefix: str) -> str:
        global _pipeline_counter
        
        # Validate job_id if provided
        if data.job_id and data.job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {data.job_id} was not found."
            )
            
        # Prevent concurrent runs
        for run in _pipeline_runs_db.values():
            if run["job_id"] == data.job_id and run["status"] == PipelineStatus.RUNNING:
                raise HireSenseException(
                    status_code=409,
                    code="PIPELINE_ALREADY_RUNNING",
                    message="A pipeline is already running."
                )
                
        _pipeline_counter += 1
        run_id = f"pipe_{run_type_prefix}_{_pipeline_counter:03d}"
        
        now_str = datetime.utcnow().isoformat() + "Z"
        run_record = {
            "pipeline_run_id": run_id,
            "job_id": data.job_id,
            "trigger_mode": data.trigger_mode,
            "status": PipelineStatus.QUEUED,
            "created_at": now_str,
            "updated_at": now_str,
            "retry_count": 0,
            "error_message": None
        }
        _pipeline_runs_db[run_id] = run_record
        return run_id

    @staticmethod
    def trigger_ingest(data: PipelineRunRequest, request_id: str, background_tasks: BackgroundTasks) -> PipelineRunResponse:
        run_id = PipelineService._create_run(data, "ingest")
        background_tasks.add_task(
            _execute_run_with_retries,
            run_id, _run_ingest_step, "CANDIDATE_JOB", "INGEST"
        )
        return PipelineRunResponse(
            request_id=request_id,
            pipeline_run_id=run_id,
            status=PipelineStatus.QUEUED
        )

    @staticmethod
    def trigger_embeddings_refresh(data: PipelineRunRequest, request_id: str, background_tasks: BackgroundTasks) -> PipelineRunResponse:
        run_id = PipelineService._create_run(data, "emb")
        background_tasks.add_task(
            _execute_run_with_retries,
            run_id, _run_embeddings_refresh_step, "SEMANTIC_SEARCH", "EMBEDDING_REFRESH"
        )
        return PipelineRunResponse(
            request_id=request_id,
            pipeline_run_id=run_id,
            status=PipelineStatus.QUEUED
        )

    @staticmethod
    def trigger_ranking_sync(data: PipelineRunRequest, request_id: str, background_tasks: BackgroundTasks) -> PipelineRunResponse:
        run_id = PipelineService._create_run(data, "rank")
        background_tasks.add_task(
            _execute_run_with_retries,
            run_id, _run_ranking_sync_step, "RANKING", "RANKING_SYNC"
        )
        return PipelineRunResponse(
            request_id=request_id,
            pipeline_run_id=run_id,
            status=PipelineStatus.QUEUED
        )

    @staticmethod
    def trigger_analytics_refresh(data: PipelineRunRequest, request_id: str, background_tasks: BackgroundTasks) -> PipelineRunResponse:
        run_id = PipelineService._create_run(data, "an")
        background_tasks.add_task(
            _execute_run_with_retries,
            run_id, _run_analytics_refresh_step, "ANALYTICS", "ANALYTICS_REFRESH"
        )
        return PipelineRunResponse(
            request_id=request_id,
            pipeline_run_id=run_id,
            status=PipelineStatus.QUEUED
        )

    @staticmethod
    def get_pipeline_run(pipeline_run_id: str, request_id: str) -> PipelineRunDetailResponse:
        if pipeline_run_id not in _pipeline_runs_db:
            raise HireSenseException(
                status_code=404,
                code="PIPELINE_RUN_NOT_FOUND",
                message=f"Pipeline run with ID {pipeline_run_id} was not found."
            )
        run = _pipeline_runs_db[pipeline_run_id]
        return PipelineRunDetailResponse(
            request_id=request_id,
            run=PipelineRunDetail(**run)
        )

    @staticmethod
    def get_pipeline_failures(request_id: str) -> PipelineFailuresResponse:
        items = [PipelineFailureItem(**f) for f in _pipeline_failures_db.values()]
        return PipelineFailuresResponse(
            request_id=request_id,
            items=items
        )
