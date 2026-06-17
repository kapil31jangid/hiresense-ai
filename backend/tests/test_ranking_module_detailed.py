import pytest
import csv
import io
from fastapi.testclient import TestClient

from app.main import app
from app.modules.job.service import _jobs_db, _job_requirements_db
from app.modules.candidate.service import _candidates_db, _candidate_evidence_db
from app.modules.ranking.service import _rankings_db
from app.modules.semantic_search.service import _embeddings_db

client = TestClient(app)
RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}

@pytest.fixture(autouse=True)
def clean_database_sandboxing():
    """Resets the mock databases for jobs, candidates, rankings, and embeddings before each test."""
    _jobs_db.clear()
    _job_requirements_db.clear()
    _candidates_db.clear()
    _candidate_evidence_db.clear()
    _rankings_db.clear()
    _embeddings_db.clear()
    
    # Re-seed a default job for standard validation
    from app.common.schemas import JobStatus
    _jobs_db["JOB_0000001"] = {
        "job_id": "JOB_0000001",
        "title": "Senior Backend Engineer",
        "status": JobStatus.ACTIVE,
        "required_skills": ["python", "fastapi", "postgresql"],
        "preferred_skills": ["distributed_systems"],
        "confidence_score": 0.93,
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:45:00Z",
        "candidate_count": 0,
        "description_text": "Looking for a Python Backend Engineer with strong FastAPI and PostgreSQL experience."
    }
    _job_requirements_db["JOB_0000001"] = [
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "python", "source_text": "Python", "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "fastapi", "source_text": "FastAPI", "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "postgresql", "source_text": "PostgreSQL", "confidence_score": 0.95},
        {"requirement_type": "PREFERRED_SKILL", "canonical_value": "distributed_systems", "source_text": "distributed systems", "confidence_score": 0.82}
    ]

def test_ranking_happy_path_and_metadata():
    # 1. Create two candidates in the mock DB
    # Candidate A: perfect fit, has embeddings & evidence
    _candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001",
        "full_name": "Alice Green",
        "normalized_skills": ["python", "fastapi", "postgresql", "distributed_systems"],
        "years_of_experience": 5.0,
        "confidence_score": 0.90,
        "parsing_status": "COMPLETED",
        "created_at": "2026-05-27T15:00:00Z",
        "updated_at": "2026-05-27T15:00:00Z"
    }
    _candidate_evidence_db["CAND_0000001"] = [
        {"candidate_experience_evidence_id": "ev_1", "candidate_id": "CAND_0000001", "evidence_type": "SKILL", "canonical_value": "python", "source_text": "Python engineer", "created_at": "2026-05-27T15:00:00Z"},
        {"candidate_experience_evidence_id": "ev_2", "candidate_id": "CAND_0000001", "evidence_type": "SKILL", "canonical_value": "fastapi", "source_text": "FastAPI APIs", "created_at": "2026-05-27T15:00:00Z"},
        {"candidate_experience_evidence_id": "ev_3", "candidate_id": "CAND_0000001", "evidence_type": "SKILL", "canonical_value": "postgresql", "source_text": "Postgres DB", "created_at": "2026-05-27T15:00:00Z"}
    ]
    _embeddings_db["emb_cand_CAND_0000001"] = {"status": "READY", "embedding_version": "candidate_profile_v1"}

    # Candidate B: partial fit, missing postgresql, has embeddings & evidence
    _candidates_db["CAND_0000002"] = {
        "candidate_id": "CAND_0000002",
        "full_name": "Bob Blue",
        "normalized_skills": ["python", "fastapi"],
        "years_of_experience": 3.0,
        "confidence_score": 0.85,
        "parsing_status": "COMPLETED",
        "created_at": "2026-05-27T15:00:00Z",
        "updated_at": "2026-05-27T15:00:00Z"
    }
    _candidate_evidence_db["CAND_0000002"] = [
        {"candidate_experience_evidence_id": "ev_4", "candidate_id": "CAND_0000002", "evidence_type": "SKILL", "canonical_value": "python", "source_text": "Python programmer", "created_at": "2026-05-27T15:00:00Z"},
        {"candidate_experience_evidence_id": "ev_5", "candidate_id": "CAND_0000002", "evidence_type": "SKILL", "canonical_value": "fastapi", "source_text": "FastAPI web dev", "created_at": "2026-05-27T15:00:00Z"}
    ]
    _embeddings_db["emb_cand_CAND_0000002"] = {"status": "READY", "embedding_version": "candidate_profile_v1"}

    # Mock semantic search returns high scores
    from app.modules.semantic_search.service import _candidate_vector_keys, _candidate_index
    import faiss
    import numpy as np
    _candidate_vector_keys.append("CAND_0000001")
    _candidate_vector_keys.append("CAND_0000002")
    _candidate_index = faiss.IndexFlatIP(384)
    # Add dummy unit-normalized vectors to index
    dummy_vecs = np.zeros((2, 384), dtype="float32")
    dummy_vecs[0, 0] = 1.0  # highly similar
    dummy_vecs[1, 0] = 0.95
    _candidate_index.add(dummy_vecs)
    from app.modules.semantic_search.service import _candidate_last_rebuilt_at
    import app.modules.semantic_search.service as ss_service
    ss_service._candidate_last_rebuilt_at = "2026-05-27T15:00:00Z"

    # 2. Run ranking via POST /api/v1/rankings
    payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_0000001", "CAND_0000002"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    ranking_id = response.json()["ranking"]["ranking_id"]
    assert ranking_id.startswith("rank_")

    # 3. Get ranking metadata
    meta_response = client.get(f"/api/v1/rankings/{ranking_id}", headers=RECRUITER_HEADERS)
    assert meta_response.status_code == 200
    assert meta_response.json()["ranking"]["ranking_id"] == ranking_id
    assert meta_response.json()["ranking"]["candidate_count"] == 2

    # 4. Get ranked candidates
    candidates_response = client.get(f"/api/v1/rankings/{ranking_id}/candidates", headers=RECRUITER_HEADERS)
    assert candidates_response.status_code == 200
    items = candidates_response.json()["items"]
    assert len(items) == 2
    
    # Alice (CAND_0000001) must rank first due to higher fit score
    assert items[0]["candidate_id"] == "CAND_0000001"
    assert items[0]["rank_position"] == 1
    assert items[0]["fit_score"] > items[1]["fit_score"]
    
    # Bob (CAND_0000002) is missing postgresql
    assert "postgresql" in items[1]["missing_required_skills"]

    # 5. Get individual candidate details
    detail_response = client.get(f"/api/v1/rankings/{ranking_id}/candidates/CAND_0000001", headers=RECRUITER_HEADERS)
    assert detail_response.status_code == 200
    assert detail_response.json()["candidate"]["candidate_id"] == "CAND_0000001"
    assert len(detail_response.json()["candidate"]["top_match_reasons"]) > 0

def test_ranking_validation_errors():
    # Job not found -> 404
    payload = {
        "job_id": "JOB_NOT_EXIST",
        "candidate_ids": ["CAND_0000001"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

    # Candidate not found / incomplete profile -> 422
    payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_NOT_EXIST"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CANDIDATE_PROFILE_INCOMPLETE"

def test_ranking_missing_embeddings_and_evidence_penalties():
    # Candidate with READY embedding and evidence
    _candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001", "full_name": "Perfect Cand",
        "normalized_skills": ["python", "fastapi", "postgresql"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    _candidate_evidence_db["CAND_0000001"] = [
        {"candidate_experience_evidence_id": "ev_1", "candidate_id": "CAND_0000001", "evidence_type": "SKILL", "canonical_value": "python", "source_text": "Python coder", "created_at": "2026-05-27T15:00:00Z"},
        {"candidate_experience_evidence_id": "ev_2", "candidate_id": "CAND_0000001", "evidence_type": "SKILL", "canonical_value": "fastapi", "source_text": "FastAPI APIs", "created_at": "2026-05-27T15:00:00Z"},
        {"candidate_experience_evidence_id": "ev_3", "candidate_id": "CAND_0000001", "evidence_type": "SKILL", "canonical_value": "postgresql", "source_text": "Postgres DB", "created_at": "2026-05-27T15:00:00Z"}
    ]
    _embeddings_db["emb_cand_CAND_0000001"] = {"status": "READY"}

    # Candidate with missing evidence (0 evidence entries)
    _candidates_db["CAND_0000002"] = {
        "candidate_id": "CAND_0000002", "full_name": "No Evidence Cand",
        "normalized_skills": ["python", "fastapi", "postgresql"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    _embeddings_db["emb_cand_CAND_0000002"] = {"status": "READY"}

    # Candidate with missing/unready embedding
    _candidates_db["CAND_0000003"] = {
        "candidate_id": "CAND_0000003", "full_name": "No Embedding Cand",
        "normalized_skills": ["python", "fastapi", "postgresql"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    _candidate_evidence_db["CAND_0000003"] = [
        {"candidate_experience_evidence_id": "ev_6", "candidate_id": "CAND_0000003", "evidence_type": "SKILL", "canonical_value": "python", "source_text": "Python coder", "created_at": "2026-05-27T15:00:00Z"}
    ]

    payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_0000001", "CAND_0000002", "CAND_0000003"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    ranking_id = response.json()["ranking"]["ranking_id"]

    candidates_response = client.get(f"/api/v1/rankings/{ranking_id}/candidates", headers=RECRUITER_HEADERS)
    items = {item["candidate_id"]: item for item in candidates_response.json()["items"]}

    # Perfect candidate should have high confidence
    assert items["CAND_0000001"]["confidence_score"] >= 0.80
    
    # Candidate with no evidence must be penalized (confidence_score lower than CAND_0000001)
    assert items["CAND_0000002"]["confidence_score"] < items["CAND_0000001"]["confidence_score"]
    
    # Candidate with no ready embedding must be penalized
    assert items["CAND_0000003"]["confidence_score"] < items["CAND_0000001"]["confidence_score"]

def test_ranking_missing_skill_penalties():
    _candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001", "full_name": "No Python Cand",
        "normalized_skills": ["fastapi", "postgresql"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    _candidates_db["CAND_0000002"] = {
        "candidate_id": "CAND_0000002", "full_name": "Only Postgres Cand",
        "normalized_skills": ["postgresql"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_0000001", "CAND_0000002"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    ranking_id = response.json()["ranking"]["ranking_id"]

    candidates_response = client.get(f"/api/v1/rankings/{ranking_id}/candidates", headers=RECRUITER_HEADERS)
    items = {item["candidate_id"]: item for item in candidates_response.json()["items"]}

    # Bob (missing two required skills) must have a lower fit score than Alice (missing one required skill)
    assert items["CAND_0000002"]["fit_score"] < items["CAND_0000001"]["fit_score"]
    assert "python" in items["CAND_0000001"]["missing_required_skills"]
    assert "fastapi" in items["CAND_0000002"]["missing_required_skills"]

def test_ranking_export_uses_stored_results():
    _candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001", "full_name": "Perfect Cand",
        "normalized_skills": ["python", "fastapi", "postgresql", "distributed_systems"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    _embeddings_db["emb_cand_CAND_0000001"] = {"status": "READY"}
    
    payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_0000001"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    ranking_id = response.json()["ranking"]["ranking_id"]

    # 1. Export CSV
    export_response = client.get(f"/api/v1/rankings/{ranking_id}/export/csv", headers=RECRUITER_HEADERS)
    assert export_response.status_code == 200
    export_data = export_response.json()
    assert "download_url" in export_data

    # 2. Modify candidate in DB before downloading CSV to prove it uses stored (static) results
    _candidates_db["CAND_0000001"]["normalized_skills"] = [] # would result in 0.0 fit if recomputed

    # 3. Retrieve CSV content
    download_url = export_data["download_url"]
    csv_response = client.get(download_url)
    assert csv_response.status_code == 200
    
    csv_text = csv_response.text
    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    rows = list(reader)
    
    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "CAND_0000001"
    # Fit score must remain high (stored value), not 0.0 (recomputed value)
    assert float(rows[0]["fit_score"]) > 0.5

def test_ranking_refresh_updates_stored_results():
    _candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001", "full_name": "Python Cand",
        "normalized_skills": ["python"], "years_of_experience": 5.0,
        "confidence_score": 0.90, "parsing_status": "COMPLETED"
    }
    payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_0000001"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=payload, headers=RECRUITER_HEADERS)
    ranking_id = response.json()["ranking"]["ranking_id"]

    # Initially fit score is low because missing fastapi and postgresql
    cands_response = client.get(f"/api/v1/rankings/{ranking_id}/candidates", headers=RECRUITER_HEADERS)
    initial_fit = cands_response.json()["items"][0]["fit_score"]

    # Update candidate profile to include missing skills
    _candidates_db["CAND_0000001"]["normalized_skills"] = ["python", "fastapi", "postgresql"]

    # Call POST /api/v1/rankings/{ranking_id}/refresh
    refresh_response = client.post(f"/api/v1/rankings/{ranking_id}/refresh", headers=RECRUITER_HEADERS)
    assert refresh_response.status_code == 200

    # Fetch candidates again and verify fit score increased
    cands_response2 = client.get(f"/api/v1/rankings/{ranking_id}/candidates", headers=RECRUITER_HEADERS)
    refreshed_fit = cands_response2.json()["items"][0]["fit_score"]
    assert refreshed_fit > initial_fit
