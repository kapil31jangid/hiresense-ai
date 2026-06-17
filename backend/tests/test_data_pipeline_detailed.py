import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.modules.ranking.service import _rankings_db
from app.modules.data_pipeline.service import (
    _pipeline_runs_db, _pipeline_failures_db, _last_successful_checkpoint
)
import app.modules.data_pipeline.service as pipeline_service
from app.modules.analytics.service import _analytics_last_updated_at

client = TestClient(app)
ADMIN_HEADERS = {"Authorization": "Bearer admin_token"}

@pytest.fixture
def clean_pipeline_sandboxing():
    """Resets databases and state for pipeline tests."""
    _jobs_db.clear()
    _candidates_db.clear()
    _rankings_db.clear()
    _pipeline_runs_db.clear()
    _pipeline_failures_db.clear()
    
    # Reset checkpoint
    pipeline_service._last_successful_checkpoint = datetime(2026, 5, 27, 0, 0, 0)
    pipeline_service._pipeline_counter = 0
    pipeline_service._failure_counter = 0

    # Seed default Job
    _jobs_db["JOB_0000001"] = {
        "job_id": "JOB_0000001",
        "title": "Senior Backend Engineer",
        "status": "ACTIVE",
        "required_skills": ["python", "fastapi", "postgresql"],
        "preferred_skills": ["distributed_systems"],
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:45:00Z"
    }

def test_pipeline_refresh_orchestration_happy_paths(clean_pipeline_sandboxing):
    # 1. Ingest run
    payload = {"job_id": "JOB_0000001", "trigger_mode": "MANUAL"}
    response = client.post("/api/v1/pipeline/runs/ingest", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    run_id_ingest = response.json()["pipeline_run_id"]
    assert run_id_ingest.startswith("pipe_ingest_")
    assert response.json()["status"] == "QUEUED"

    # Since TestClient runs background tasks synchronously, we can query status immediately
    status_resp = client.get(f"/api/v1/pipeline/runs/{run_id_ingest}", headers=ADMIN_HEADERS)
    assert status_resp.status_code == 200
    assert status_resp.json()["run"]["status"] == "COMPLETED"

    # 2. Embeddings refresh run
    response = client.post("/api/v1/pipeline/runs/embeddings-refresh", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    run_id_emb = response.json()["pipeline_run_id"]
    
    status_resp = client.get(f"/api/v1/pipeline/runs/{run_id_emb}", headers=ADMIN_HEADERS)
    assert status_resp.json()["run"]["status"] == "COMPLETED"

    # Seed a ranking so sync has something to touch
    _rankings_db["rank_001"] = {
        "ranking_id": "rank_001",
        "job_id": "JOB_0000001",
        "status": "COMPLETED",
        "created_at": "2026-05-27T15:20:00Z",
        "candidates": []
    }

    # 3. Ranking Sync run
    response = client.post("/api/v1/pipeline/runs/ranking-sync", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    run_id_rank = response.json()["pipeline_run_id"]
    
    status_resp = client.get(f"/api/v1/pipeline/runs/{run_id_rank}", headers=ADMIN_HEADERS)
    assert status_resp.json()["run"]["status"] == "COMPLETED"

    # 4. Analytics Refresh run
    prev_freshness = client.get("/api/v1/analytics/dashboard", headers=ADMIN_HEADERS).json()["analytics_last_updated_at"]
    response = client.post("/api/v1/pipeline/runs/analytics-refresh", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    run_id_an = response.json()["pipeline_run_id"]
    
    status_resp = client.get(f"/api/v1/pipeline/runs/{run_id_an}", headers=ADMIN_HEADERS)
    assert status_resp.json()["run"]["status"] == "COMPLETED"

    # Verify analytics last updated at was refreshed
    curr_freshness = client.get("/api/v1/analytics/dashboard", headers=ADMIN_HEADERS).json()["analytics_last_updated_at"]
    assert curr_freshness != prev_freshness

def test_pipeline_validation_errors(clean_pipeline_sandboxing):
    # Job not found -> 404
    payload = {"job_id": "JOB_NOT_EXIST", "trigger_mode": "MANUAL"}
    response = client.post("/api/v1/pipeline/runs/ranking-sync", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

    # Prevent concurrent runs -> 409
    # Start a run, manually set status to RUNNING in the DB to simulate concurrency
    payload_ok = {"job_id": "JOB_0000001", "trigger_mode": "MANUAL"}
    response1 = client.post("/api/v1/pipeline/runs/ranking-sync", json=payload_ok, headers=ADMIN_HEADERS)
    run_id = response1.json()["pipeline_run_id"]
    
    _pipeline_runs_db[run_id]["status"] = "RUNNING"
    
    response2 = client.post("/api/v1/pipeline/runs/ranking-sync", json=payload_ok, headers=ADMIN_HEADERS)
    assert response2.status_code == 409
    assert response2.json()["error"]["code"] == "PIPELINE_ALREADY_RUNNING"

def test_pipeline_retry_exhaustion_and_checkpoint_preservation(clean_pipeline_sandboxing):
    # Set job_id to trigger simulated ingest failure
    payload = {"job_id": "JOB_FAIL_INGEST", "trigger_mode": "MANUAL"}
    
    # Before run, get the checkpoint timestamp
    checkpoint_before = pipeline_service._last_successful_checkpoint
    
    # Seed JOB_FAIL_INGEST in jobs DB to pass validation
    _jobs_db["JOB_FAIL_INGEST"] = {
        "job_id": "JOB_FAIL_INGEST",
        "title": "Failing Job",
        "status": "ACTIVE",
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:30:00Z"
    }
    
    response = client.post("/api/v1/pipeline/runs/ingest", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    run_id = response.json()["pipeline_run_id"]
    
    # Verify run failed
    status_resp = client.get(f"/api/v1/pipeline/runs/{run_id}", headers=ADMIN_HEADERS)
    assert status_resp.json()["run"]["status"] == "FAILED"
    assert status_resp.json()["run"]["retry_count"] == 2 # 0, 1, 2 attempts (total 3 attempts)
    assert status_resp.json()["run"]["error_message"] == "Ingest step failed."
    
    # Verify failures store logged the dead-letter metadata
    failures_resp = client.get("/api/v1/pipeline/failures", headers=ADMIN_HEADERS)
    assert failures_resp.status_code == 200
    failures = failures_resp.json()["items"]
    assert len(failures) == 1
    assert failures[0]["pipeline_run_id"] == run_id
    assert failures[0]["failure_stage"] == "INGEST"
    assert failures[0]["error_message"] == "Ingest step failed."
    
    # Verify checkpoint preserved (unchanged)
    assert pipeline_service._last_successful_checkpoint == checkpoint_before

def test_pipeline_incremental_refresh_touches_affected_records_only(clean_pipeline_sandboxing):
    # Seed candidates
    _candidates_db["CAND_001"] = {
        "candidate_id": "CAND_001",
        "full_name": "Alice Green",
        "updated_at": "2026-05-27T15:00:00Z"
    }
    _candidates_db["CAND_002"] = {
        "candidate_id": "CAND_002",
        "full_name": "Bob Blue",
        "updated_at": "2026-05-27T15:00:00Z"
    }

    # Set last checkpoint to 2026-05-27T15:15:00Z (newer than candidates updates)
    pipeline_service._last_successful_checkpoint = datetime(2026, 5, 27, 15, 15, 0)
    
    # Create ingest run without specific job (global sync)
    payload = {"trigger_mode": "SCHEDULED"}
    response = client.post("/api/v1/pipeline/runs/ingest", json=payload, headers=ADMIN_HEADERS)
    run_id = response.json()["pipeline_run_id"]
    
    # Since candidates updated before checkpoint, they should NOT be processed
    run_detail = _pipeline_runs_db[run_id]
    assert len(run_detail.get("processed_candidates", [])) == 0

    # Now touch Bob Blue (CAND_002) to simulate modification
    _candidates_db["CAND_002"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    response2 = client.post("/api/v1/pipeline/runs/ingest", json=payload, headers=ADMIN_HEADERS)
    run_id2 = response2.json()["pipeline_run_id"]
    
    # Only Bob Blue (CAND_002) should be processed
    run_detail2 = _pipeline_runs_db[run_id2]
    assert run_detail2.get("processed_candidates") == ["CAND_002"]

def test_pipeline_failures_preserve_analytics_freshness(clean_pipeline_sandboxing):
    # Set job_id to trigger simulated analytics failure
    payload = {"job_id": "JOB_FAIL_ANALYTICS", "trigger_mode": "MANUAL"}
    
    # Seed JOB_FAIL_ANALYTICS in jobs DB
    _jobs_db["JOB_FAIL_ANALYTICS"] = {
        "job_id": "JOB_FAIL_ANALYTICS",
        "title": "Failing Job",
        "status": "ACTIVE",
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:30:00Z"
    }
    
    # Get previous freshness
    prev_freshness = client.get("/api/v1/analytics/dashboard", headers=ADMIN_HEADERS).json()["analytics_last_updated_at"]
    
    response = client.post("/api/v1/pipeline/runs/analytics-refresh", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    
    # Verify run failed
    run_id = response.json()["pipeline_run_id"]
    status_resp = client.get(f"/api/v1/pipeline/runs/{run_id}", headers=ADMIN_HEADERS)
    assert status_resp.json()["run"]["status"] == "FAILED"
    
    # Verify freshness did not update
    curr_freshness = client.get("/api/v1/analytics/dashboard", headers=ADMIN_HEADERS).json()["analytics_last_updated_at"]
    assert curr_freshness == prev_freshness
