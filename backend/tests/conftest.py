from datetime import datetime, timezone

import numpy as np
import faiss
import pytest

from app.common.schemas import AlertSeverity, AlertStatus, JobStatus, RankingStatus, FreshnessStatus
from app.modules.alerts import service as alerts_service
from app.modules.analytics.service import AnalyticsService
from app.modules.candidate import service as candidate_service
from app.modules.job import service as job_service
from app.modules.ranking import service as ranking_service
from app.modules.semantic_search import service as semantic_search_service


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@pytest.fixture(autouse=True)
def seed_demo_state():
    job_service._jobs_db.clear()
    job_service._job_requirements_db.clear()
    candidate_service._candidates_db.clear()
    candidate_service._candidate_evidence_db.clear()
    ranking_service._rankings_db.clear()
    alerts_service._alerts_db.clear()
    alerts_service._alert_events_db.clear()
    semantic_search_service._embeddings_db.clear()
    semantic_search_service._candidate_vectors.clear()
    semantic_search_service._job_vectors.clear()
    semantic_search_service._candidate_vector_keys.clear()
    semantic_search_service._job_vector_keys.clear()
    semantic_search_service._candidate_index = None
    semantic_search_service._job_index = None
    semantic_search_service._candidate_last_rebuilt_at = None
    semantic_search_service._job_last_rebuilt_at = None

    now = _now()

    job_service._jobs_db["JOB_0000001"] = {
        "job_id": "JOB_0000001",
        "title": "Senior Backend Engineer",
        "status": JobStatus.ACTIVE,
        "required_skills": ["python", "fastapi", "postgresql"],
        "preferred_skills": ["distributed_systems"],
        "confidence_score": 0.93,
        "created_at": now,
        "updated_at": now,
        "candidate_count": 42,
        "description_text": (
            "We are hiring a Senior Backend Engineer with strong Python, FastAPI, "
            "PostgreSQL, and distributed systems experience."
        ),
        "role_intelligence": {},
        "embedding_metadata": {"status": "READY", "embedding_version": "job_requirements_v1"},
    }
    job_service._job_requirements_db["JOB_0000001"] = [
        {
            "requirement_type": "REQUIRED_SKILL",
            "canonical_value": "python",
            "source_text": "strong Python, FastAPI, PostgreSQL",
            "source_span_start": 53,
            "source_span_end": 88,
            "confidence_score": 0.95,
        },
        {
            "requirement_type": "REQUIRED_SKILL",
            "canonical_value": "fastapi",
            "source_text": "strong Python, FastAPI, PostgreSQL",
            "source_span_start": 53,
            "source_span_end": 88,
            "confidence_score": 0.95,
        },
        {
            "requirement_type": "REQUIRED_SKILL",
            "canonical_value": "postgresql",
            "source_text": "strong Python, FastAPI, PostgreSQL",
            "source_span_start": 53,
            "source_span_end": 88,
            "confidence_score": 0.95,
        },
        {
            "requirement_type": "PREFERRED_SKILL",
            "canonical_value": "distributed_systems",
            "source_text": "distributed systems experience",
            "source_span_start": 94,
            "source_span_end": 124,
            "confidence_score": 0.82,
        },
    ]
    job_service._job_counter = 1

    candidate_service._candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001",
        "full_name": "Alice Green",
        "normalized_skills": ["python", "fastapi", "postgresql", "distributed_systems"],
        "years_of_experience": 5.0,
        "confidence_score": 0.90,
        "parsing_status": "COMPLETED",
        "created_at": now,
        "updated_at": now,
        "source_type": "TEXT",
        "source_file_name": None,
        "source_text": "Python FastAPI PostgreSQL distributed systems",
        "source_data": {},
        "profile": {"full_name": "Alice Green", "email": "alice@example.com"},
        "career_history": [],
        "education": [],
        "skills": ["python", "fastapi", "postgresql", "distributed_systems"],
        "redrob_signals": ["collaboration"],
        "behavioral_signals": ["collaboration"],
        "embedding_metadata": {"status": "READY", "embedding_version": "candidate_profile_v1"},
    }
    candidate_service._candidate_evidence_db["CAND_0000001"] = [
        {
            "candidate_experience_evidence_id": "ev_1",
            "candidate_id": "CAND_0000001",
            "evidence_type": "SKILL",
            "canonical_value": "python",
            "source_text": "Python engineer",
            "created_at": now,
        },
        {
            "candidate_experience_evidence_id": "ev_2",
            "candidate_id": "CAND_0000001",
            "evidence_type": "SKILL",
            "canonical_value": "fastapi",
            "source_text": "FastAPI APIs",
            "created_at": now,
        },
        {
            "candidate_experience_evidence_id": "ev_3",
            "candidate_id": "CAND_0000001",
            "evidence_type": "SKILL",
            "canonical_value": "postgresql",
            "source_text": "Postgres DB",
            "created_at": now,
        },
    ]
    candidate_service._candidate_counter = 1
    candidate_service._evidence_counter = 3

    ranking_service._rankings_db["rank_001"] = {
        "ranking_id": "rank_001",
        "job_id": "JOB_0000001",
        "status": RankingStatus.COMPLETED,
        "candidate_count": 1,
        "created_at": now,
        "updated_at": now,
        "candidates": [
            {
                "candidate_id": "CAND_0000001",
                "rank_position": 1,
                "fit_score": 0.91,
                "confidence_score": 0.87,
                "missing_required_skills": [],
                "top_match_reasons": [
                    "Strong semantic match for backend platform work",
                    "Direct evidence of FastAPI and PostgreSQL experience",
                ],
                "semantic_score": 0.94,
            }
        ],
    }
    ranking_service._ranking_counter = 1

    alerts_service._alerts_db["alert_rank_001"] = {
        "alert_id": "alert_rank_001",
        "alert_type": "LOW_CONFIDENCE_RANKING",
        "condition_key": "LOW_CONFIDENCE_RANKING:rank_001",
        "source_entity_id": "rank_001",
        "status": AlertStatus.ACTIVE,
        "severity": AlertSeverity.HIGH,
        "title": "Ranking confidence is low for Senior Backend Engineer",
        "message": "Required skill evidence is incomplete for top candidates.",
        "created_at": now,
        "job_id": "JOB_0000001",
        "candidate_id": None,
        "ranking_id": "rank_001",
        "acknowledged_at": None,
        "acknowledged_by": None,
        "resolved_at": None,
        "resolved_by": None,
        "resolution_note": None,
        "last_evaluated_at": now,
    }
    alerts_service._alert_events_db["evt_001"] = {
        "event_id": "evt_001",
        "alert_id": "alert_rank_001",
        "from_status": None,
        "to_status": "ACTIVE",
        "changed_by": "system",
        "changed_at": now,
        "notes": "Alert created by system evaluation.",
    }
    alerts_service._alert_counter = 1
    alerts_service._event_counter = 1

    semantic_search_service._candidate_vectors["CAND_0000001"] = np.zeros(384, dtype="float32")
    semantic_search_service._candidate_vectors["CAND_0000001"][0] = 1.0
    semantic_search_service._job_vectors["JOB_0000001"] = np.zeros(384, dtype="float32")
    semantic_search_service._job_vectors["JOB_0000001"][0] = 1.0
    semantic_search_service._candidate_index = faiss.IndexFlatIP(384)
    semantic_search_service._candidate_index.add(
        np.array([semantic_search_service._candidate_vectors["CAND_0000001"]], dtype="float32")
    )
    semantic_search_service._job_index = faiss.IndexFlatIP(384)
    semantic_search_service._job_index.add(
        np.array([semantic_search_service._job_vectors["JOB_0000001"]], dtype="float32")
    )
    semantic_search_service._candidate_vector_keys[:] = ["CAND_0000001"]
    semantic_search_service._job_vector_keys[:] = ["JOB_0000001"]
    semantic_search_service._candidate_last_rebuilt_at = now
    semantic_search_service._job_last_rebuilt_at = now
    semantic_search_service._embeddings_db["emb_cand_CAND_0000001"] = {
        "embedding_id": "emb_cand_CAND_0000001",
        "entity_type": "CANDIDATE",
        "entity_id": "CAND_0000001",
        "embedding_version": "candidate_profile_v1",
        "status": "READY",
        "source_hash": "seed",
        "created_at": now,
        "updated_at": now,
    }
    semantic_search_service._embeddings_db["emb_job_JOB_0000001"] = {
        "embedding_id": "emb_job_JOB_0000001",
        "entity_type": "JOB",
        "entity_id": "JOB_0000001",
        "embedding_version": "job_requirements_v1",
        "status": "READY",
        "source_hash": "seed",
        "created_at": now,
        "updated_at": now,
    }

    AnalyticsService.refresh_aggregates(now, FreshnessStatus.FRESH)
    yield
