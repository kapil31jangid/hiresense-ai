from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import faiss
import pytest

from app.common.schemas import AlertSeverity, AlertStatus, JobStatus, RankingStatus, FreshnessStatus
from app.main import app
from app.modules.alerts import service as alerts_service
from app.modules.ai import service as ai_service
from app.modules.analytics.service import AnalyticsService
from app.modules.candidate import service as candidate_service
from app.challenge import dataset_store as challenge_dataset
from app.modules.data_pipeline import service as pipeline_service
from app.modules.job import service as job_service
from app.modules.ranking import service as ranking_service
from app.modules.semantic_search import service as semantic_search_service


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@pytest.fixture(autouse=True)
def seed_demo_state(monkeypatch):
    monkeypatch.setattr(challenge_dataset, "is_enabled", lambda: False, raising=False)
    monkeypatch.setattr(challenge_dataset, "list_summaries", lambda: [], raising=False)
    monkeypatch.setattr(challenge_dataset, "has_candidate", lambda candidate_id: False, raising=False)
    monkeypatch.setattr(challenge_dataset, "get_candidate", lambda candidate_id: None, raising=False)

    class _FakeBlob:
        def __init__(self, storage: dict, name: str):
            self._storage = storage
            self._name = name

        def upload_from_string(self, data: str, content_type: str = "text/plain"):
            self._storage[self._name] = data.encode("utf-8") if isinstance(data, str) else data

        def upload_from_filename(self, filename: str, content_type: str = "text/plain"):
            with open(filename, "rb") as f:
                self._storage[self._name] = f.read()

        def exists(self):
            return self._name in self._storage

        def download_to_filename(self, filename: str):
            with open(filename, "wb") as f:
                f.write(self._storage[self._name])

    class _FakeBucket:
        def __init__(self, storage: dict):
            self._storage = storage

        def blob(self, name: str):
            return _FakeBlob(self._storage, name)

    class _FakeGCSClient:
        def __init__(self):
            self._storage = {}

        def bucket(self, bucket_name: str):
            return _FakeBucket(self._storage)

    def _verify_id_token(token: str, check_revoked: bool = False):
        mapping = {
            "recruiter_token": {"uid": "user_recruiter_001", "role": "RECRUITER", "tenant_id": "tenant_001"},
            "admin_token": {"uid": "user_admin_001", "role": "ADMIN", "tenant_id": "tenant_001"},
        }
        if token not in mapping:
            raise ValueError("Invalid Firebase ID token.")
        return mapping[token]

    monkeypatch.setattr("firebase_admin.auth.verify_id_token", _verify_id_token, raising=False)

    runtime = getattr(app.state, "runtime", None)
    if runtime is not None:
        runtime.firebase_ready = True
        runtime.firebase_status = "ready"
        runtime.firestore_ready = True
        runtime.firestore_status = "ready"
        runtime.gcs_ready = True
        runtime.gcs_status = "ready"
        runtime.gcs_client = _FakeGCSClient()

    fake_runtime = SimpleNamespace(
        settings=SimpleNamespace(
            google_api_key="test-gemini-key",
            gemini_model_name="gemini-1.5-flash",
            gcs_bucket_name="hiresense-ai",
            google_cloud_project="hiresense-ai",
        ),
        firebase_ready=True,
        firestore_ready=True,
        gcs_ready=True,
        gemini_ready=True,
        faiss_ready=True,
        gcs_client=runtime.gcs_client if runtime is not None and runtime.gcs_client is not None else _FakeGCSClient(),
        should_use_gemini=lambda: True,
        dependency_statuses=lambda: {
            "firebase_auth": "ready",
            "firestore": "ready",
            "postgresql": "ready",
            "database": "firestore",
            "gcs": "ready",
            "object_storage": "ready",
            "gemini": "configured",
            "ai_provider": "configured",
            "faiss": "ok",
        },
    )
    app.state.runtime = fake_runtime

    memory_only_runtime = SimpleNamespace(firestore_ready=False, firestore_client=None)
    for store in (
        job_service._jobs_db,
        job_service._job_requirements_db,
        candidate_service._candidates_db,
        candidate_service._candidate_evidence_db,
        ranking_service._rankings_db,
        alerts_service._alerts_db,
        alerts_service._alert_events_db,
        semantic_search_service._embeddings_db,
        semantic_search_service._index_metadata_db,
        pipeline_service._pipeline_runs_db,
        pipeline_service._pipeline_failures_db,
    ):
        if hasattr(store, "_runtime"):
            store._runtime = memory_only_runtime

    def _fake_gemini(prompt: str) -> str:
        lowered = prompt.lower()
        if "skills_used:" in lowered:
            confidence_line = next((line for line in prompt.splitlines() if line.startswith("confidence_score:")), "confidence_score: 0")
            skills_line = next((line for line in prompt.splitlines() if line.startswith("skills_used:")), "skills_used: none")
            missing_line = next((line for line in prompt.splitlines() if line.startswith("missing_required_skills:")), "missing_required_skills: none")
            skills = skills_line.split(":", 1)[1].strip()
            missing = missing_line.split(":", 1)[1].strip()
            confidence = float(confidence_line.split(":", 1)[1].strip())
            if missing == "none":
                missing_text = "No required skills are missing."
            else:
                missing_text = f"Missing required skills: {missing}. Note that some parsed resume evidence is partial."
            confidence_text = ""
            if confidence < 0.65:
                confidence_text = " This candidate has a low ranking confidence score. The fit should be manually reviewed before final shortlisting."
            return f"This candidate has evidence of {skills} experience. {missing_text}{confidence_text}"
        if "top_candidate:" in lowered:
            total_line = next((line for line in prompt.splitlines() if line.startswith("total_candidates:")), "total_candidates: 0")
            top_line = next((line for line in prompt.splitlines() if line.startswith("top_candidate:")), "top_candidate: Candidate")
            missing_line = next((line for line in prompt.splitlines() if line.startswith("missing_required_skills:")), "missing_required_skills: none")
            total = total_line.split(":", 1)[1].strip()
            top = top_line.split(":", 1)[1].strip()
            missing = missing_line.split(":", 1)[1].strip()
            missing_text = f" Missing required skills include: {missing}." if missing != "none" else ""
            warning_text = " Warning: 1 candidate(s) have low parsing confidence and require manual review." if "low_confidence_count: 1" in lowered else ""
            return (
                f"This shortlist evaluated {total} candidates. "
                f"The top candidate is {top}. "
                f"Manual review is recommended where evidence is partial.{missing_text}{warning_text}"
            )
        if "rank=" in prompt:
            lines = [line for line in prompt.splitlines() if line.startswith("- ")]
            if len(lines) >= 2:
                first = lines[0].split("|", 1)[0].replace("- ", "").strip()
                second = lines[1].split("|", 1)[0].replace("- ", "").strip()
                return f"{first} ranks higher than {second} because the first profile shows stronger alignment and fewer missing required skills."
            if lines:
                first = lines[0].split("|", 1)[0].replace("- ", "").strip()
                return f"{first} is the strongest candidate in the supplied comparison set."
        return prompt

    monkeypatch.setattr(ranking_service, "build_runtime_state", lambda: fake_runtime, raising=False)
    monkeypatch.setattr(semantic_search_service, "build_runtime_state", lambda: fake_runtime, raising=False)
    monkeypatch.setattr(ai_service, "build_runtime_state", lambda: fake_runtime, raising=False)
    monkeypatch.setattr(
        ai_service,
        "_generate_with_gemini",
        _fake_gemini,
        raising=False,
    )

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
