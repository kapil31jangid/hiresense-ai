import copy
import sys
import types

import pytest
from fastapi.testclient import TestClient

if "numpy" not in sys.modules:
    numpy_stub = types.ModuleType("numpy")
    numpy_stub.ndarray = object
    sys.modules["numpy"] = numpy_stub

if "faiss" not in sys.modules:
    faiss_stub = types.ModuleType("faiss")

    class _IndexFlatIP:
        def __init__(self, dimension):
            self.dimension = dimension

    faiss_stub.IndexFlatIP = _IndexFlatIP
    sys.modules["faiss"] = faiss_stub

from app.common.schemas import FreshnessStatus
from app.main import app
from app.modules.alerts.service import _alerts_db
from app.modules.analytics import service as analytics_module
from app.modules.analytics.service import AnalyticsService
from app.modules.candidate.service import _candidates_db
from app.modules.job.service import _jobs_db
from app.modules.ranking.service import _rankings_db

client = TestClient(app)

RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}


@pytest.fixture(autouse=True)
def analytics_sandbox():
    original_jobs = copy.deepcopy(_jobs_db)
    original_candidates = copy.deepcopy(_candidates_db)
    original_rankings = copy.deepcopy(_rankings_db)
    original_alerts = copy.deepcopy(_alerts_db)
    original_last_updated = analytics_module._analytics_last_updated_at
    original_freshness = analytics_module._freshness_status
    original_aggregates = copy.deepcopy(analytics_module._analytics_aggregates)

    _jobs_db.clear()
    _jobs_db["JOB_ANALYTICS_001"] = {
        "job_id": "JOB_ANALYTICS_001",
        "title": "Backend Engineer",
        "status": "ACTIVE",
        "required_skills": ["python", "fastapi"],
        "preferred_skills": ["postgresql"],
        "confidence_score": 0.93,
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:45:00Z",
    }

    _candidates_db.clear()
    _candidates_db["CAND_ANALYTICS_001"] = {
        "candidate_id": "CAND_ANALYTICS_001",
        "full_name": "Aarav Sharma",
        "normalized_skills": ["python", "fastapi"],
        "confidence_score": 0.91,
        "parsing_status": "COMPLETED",
        "created_at": "2026-05-27T15:00:00Z",
        "updated_at": "2026-05-27T15:08:00Z",
    }
    _candidates_db["CAND_ANALYTICS_002"] = {
        "candidate_id": "CAND_ANALYTICS_002",
        "full_name": "Meera Rao",
        "normalized_skills": ["python"],
        "confidence_score": 0.63,
        "parsing_status": "PARTIAL",
        "created_at": "2026-05-27T15:02:00Z",
        "updated_at": "2026-05-27T15:09:00Z",
    }

    _rankings_db.clear()
    _rankings_db["rank_analytics_001"] = {
        "ranking_id": "rank_analytics_001",
        "job_id": "JOB_ANALYTICS_001",
        "status": "COMPLETED",
        "candidate_count": 2,
        "created_at": "2026-05-27T15:20:00Z",
        "updated_at": "2026-05-27T15:20:00Z",
        "candidates": [
            {
                "candidate_id": "CAND_ANALYTICS_001",
                "rank_position": 1,
                "fit_score": 0.91,
                "confidence_score": 0.89,
                "missing_required_skills": [],
            },
            {
                "candidate_id": "CAND_ANALYTICS_002",
                "rank_position": 2,
                "fit_score": 0.62,
                "confidence_score": 0.61,
                "missing_required_skills": ["fastapi"],
            },
        ],
    }

    _alerts_db.clear()
    _alerts_db["alert_analytics_001"] = {
        "alert_id": "alert_analytics_001",
        "alert_type": "LOW_CONFIDENCE_RANKING",
        "status": "ACTIVE",
        "severity": "HIGH",
        "title": "Ranking confidence is low",
        "message": "One candidate has low ranking confidence.",
        "created_at": "2026-05-27T15:25:00Z",
        "job_id": "JOB_ANALYTICS_001",
    }

    AnalyticsService.refresh_aggregates("2026-05-27T15:30:00Z", FreshnessStatus.FRESH)

    yield

    _jobs_db.clear()
    _jobs_db.update(original_jobs)
    _candidates_db.clear()
    _candidates_db.update(original_candidates)
    _rankings_db.clear()
    _rankings_db.update(original_rankings)
    _alerts_db.clear()
    _alerts_db.update(original_alerts)
    analytics_module._analytics_last_updated_at = original_last_updated
    analytics_module._freshness_status = original_freshness
    analytics_module._analytics_aggregates = original_aggregates


def test_dashboard_and_insight_aggregates_include_freshness_fields():
    dashboard_response = client.get("/api/v1/analytics/dashboard", headers=RECRUITER_HEADERS)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["analytics_last_updated_at"] == "2026-05-27T15:30:00Z"
    assert dashboard["freshness_status"] == "FRESH"
    assert dashboard["summary"] == {
        "active_jobs": 1,
        "parsed_candidates": 2,
        "active_alert_count": 1,
        "low_confidence_rankings": 1,
        "average_fit_score": 0.77,
    }

    ranking_quality_response = client.get("/api/v1/analytics/ranking-quality", headers=RECRUITER_HEADERS)
    assert ranking_quality_response.status_code == 200
    ranking_quality = ranking_quality_response.json()
    assert ranking_quality["summary"]["ranking_count"] == 1
    assert ranking_quality["summary"]["ranked_candidate_count"] == 2
    assert ranking_quality["summary"]["average_confidence_score"] == 0.75

    skill_response = client.get("/api/v1/analytics/skill-distribution", headers=RECRUITER_HEADERS)
    assert skill_response.status_code == 200
    skill_items = skill_response.json()["items"]
    assert {"skill_name": "python", "job_count": 1, "candidate_count": 2} in skill_items
    assert {"skill_name": "fastapi", "job_count": 1, "candidate_count": 1} in skill_items

    insights_response = client.get("/api/v1/analytics/hiring-insights", headers=RECRUITER_HEADERS)
    assert insights_response.status_code == 200
    insight_types = {item["insight_type"] for item in insights_response.json()["items"]}
    assert {"RANKING_QUALITY", "PIPELINE_FRESHNESS", "SKILL_DISTRIBUTION"}.issubset(insight_types)


def test_candidate_funnel_uses_stored_ranking_outputs():
    response = client.get("/api/v1/analytics/candidate-funnel", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["freshness_status"] == "FRESH"
    assert data["summary"] == {
        "uploaded_candidates": 2,
        "parsed_candidates": 2,
        "ranked_candidates": 2,
        "shortlisted_candidates": 1,
    }


def test_missing_analytics_context_returns_not_ready_error():
    analytics_module._analytics_last_updated_at = None
    analytics_module._analytics_aggregates = None

    response = client.get("/api/v1/analytics/dashboard", headers=RECRUITER_HEADERS)

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "ANALYTICS_NOT_READY"
    assert body["error"]["details"]["freshness_status"] == "FRESH"


def test_stale_aggregates_are_returned_with_stale_freshness_status():
    AnalyticsService.refresh_aggregates("2026-05-27T14:30:00Z", FreshnessStatus.STALE)

    response = client.get("/api/v1/analytics/ranking-quality", headers=RECRUITER_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["analytics_last_updated_at"] == "2026-05-27T14:30:00Z"
    assert data["freshness_status"] == "STALE"
    assert data["summary"]["low_confidence_count"] == 1


def test_analytics_reads_derived_snapshot_not_live_operational_state():
    first_response = client.get("/api/v1/analytics/dashboard", headers=RECRUITER_HEADERS)
    assert first_response.json()["summary"]["active_jobs"] == 1

    _jobs_db["JOB_ANALYTICS_002"] = {
        "job_id": "JOB_ANALYTICS_002",
        "title": "Data Engineer",
        "status": "ACTIVE",
        "required_skills": ["python"],
        "preferred_skills": [],
        "confidence_score": 0.90,
        "created_at": "2026-05-27T16:00:00Z",
        "updated_at": "2026-05-27T16:00:00Z",
    }

    stale_snapshot_response = client.get("/api/v1/analytics/dashboard", headers=RECRUITER_HEADERS)
    assert stale_snapshot_response.json()["summary"]["active_jobs"] == 1

    AnalyticsService.refresh_aggregates("2026-05-27T16:15:00Z", FreshnessStatus.FRESH)
    refreshed_response = client.get("/api/v1/analytics/dashboard", headers=RECRUITER_HEADERS)
    assert refreshed_response.json()["summary"]["active_jobs"] == 2
    assert refreshed_response.json()["analytics_last_updated_at"] == "2026-05-27T16:15:00Z"
