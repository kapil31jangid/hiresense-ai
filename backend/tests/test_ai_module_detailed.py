import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.modules.ranking.service import _rankings_db
from app.modules.ai.service import _explanations_db

client = TestClient(app)
RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}

@pytest.fixture
def clean_database_sandboxing():
    """Resets the mock databases before each test."""
    _jobs_db.clear()
    _candidates_db.clear()
    _rankings_db.clear()
    _explanations_db.clear()

    # Seed default Job
    _jobs_db["JOB_0000001"] = {
        "job_id": "JOB_0000001",
        "title": "Senior Backend Engineer",
        "status": "ACTIVE",
        "required_skills": ["python", "fastapi", "postgresql"],
        "preferred_skills": ["distributed_systems"],
        "created_at": "2026-05-27T14:30:00Z"
    }

    # Seed Candidates
    # Candidate 1: High confidence, all skills
    _candidates_db["CAND_0000001"] = {
        "candidate_id": "CAND_0000001",
        "full_name": "Alice Green",
        "normalized_skills": ["python", "fastapi", "postgresql", "distributed_systems"],
        "confidence_score": 0.90
    }
    # Candidate 2: Medium confidence, missing postgresql
    _candidates_db["CAND_0000002"] = {
        "candidate_id": "CAND_0000002",
        "full_name": "Bob Blue",
        "normalized_skills": ["python", "fastapi"],
        "confidence_score": 0.75
    }
    # Candidate 3: Low confidence, missing postgresql and fastapi
    _candidates_db["CAND_0000003"] = {
        "candidate_id": "CAND_0000003",
        "full_name": "Charlie Red",
        "normalized_skills": ["python"],
        "confidence_score": 0.50
    }

    # Seed a Completed Ranking Run
    _rankings_db["rank_001"] = {
        "ranking_id": "rank_001",
        "job_id": "JOB_0000001",
        "status": "COMPLETED",
        "candidate_count": 3,
        "created_at": "2026-05-27T15:20:00Z",
        "updated_at": "2026-05-27T15:20:00Z",
        "candidates": [
            {
                "candidate_id": "CAND_0000001",
                "rank_position": 1,
                "fit_score": 0.95,
                "confidence_score": 0.90,
                "missing_required_skills": [],
                "top_match_reasons": ["Strong skills match"],
                "semantic_score": 0.94
            },
            {
                "candidate_id": "CAND_0000002",
                "rank_position": 2,
                "fit_score": 0.75,
                "confidence_score": 0.75,
                "missing_required_skills": ["postgresql"],
                "top_match_reasons": ["Good fit but missing postgresql"],
                "semantic_score": 0.80
            },
            {
                "candidate_id": "CAND_0000003",
                "rank_position": 3,
                "fit_score": 0.45,
                "confidence_score": 0.50,
                "missing_required_skills": ["fastapi", "postgresql"],
                "top_match_reasons": ["Weak alignment"],
                "semantic_score": 0.50
            }
        ]
    }

    # Seed an Incomplete (not ready) Ranking Run
    _rankings_db["rank_not_ready"] = {
        "ranking_id": "rank_not_ready",
        "job_id": "JOB_0000001",
        "status": "PENDING",
        "candidates": []
    }

def test_generate_explanation_happy_paths(clean_database_sandboxing):
    # Test Alice (high confidence, 0.90)
    payload = {"ranking_id": "rank_001", "candidate_id": "CAND_0000001"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["ranking_id"] == "rank_001"
    assert data["candidate_id"] == "CAND_0000001"
    assert data["confidence_score"] == 0.90
    assert "python" in data["explanation"]
    assert "fastapi" in data["explanation"]
    assert "postgresql" in data["explanation"]
    assert "No required skills are missing" in data["explanation"]
    assert "evidence of python, fastapi, postgresql" in data["explanation"]
    # No warning message in high confidence
    assert "partial" not in data["explanation"]
    assert "manually reviewed" not in data["explanation"]
    assert data["grounding"]["skills_used"] == ["python", "fastapi", "postgresql"]
    assert data["grounding"]["missing_required_skills"] == []

    # Test Bob (medium confidence, 0.75)
    payload = {"ranking_id": "rank_001", "candidate_id": "CAND_0000002"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["confidence_score"] == 0.75
    assert "postgresql" in data["grounding"]["missing_required_skills"]
    assert "Note that some parsed resume evidence is partial." in data["explanation"]

    # Test Charlie (low confidence, 0.50)
    payload = {"ranking_id": "rank_001", "candidate_id": "CAND_0000003"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["confidence_score"] == 0.50
    assert "This candidate has a low ranking confidence score. The fit should be manually reviewed before final shortlisting." in data["explanation"]

def test_get_explanations_collection_and_self_healing(clean_database_sandboxing):
    # Prior to calling GET, explanations database for rank_001 is empty
    assert "rank_001" not in _explanations_db or not _explanations_db["rank_001"]

    # Call GET /api/v1/ai/explanations/rank_001
    response = client.get("/api/v1/ai/explanations/rank_001", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["ranking_id"] == "rank_001"
    assert len(data["items"]) == 3
    
    # Verify it self-healed and pre-populated explanations in db
    assert "rank_001" in _explanations_db
    assert len(_explanations_db["rank_001"]) == 3
    
    # Retrieve and verify properties of the first item (Alice)
    alice_item = data["items"][0]
    assert alice_item["candidate_id"] == "CAND_0000001"
    assert alice_item["confidence_score"] == 0.90
    assert "python" in alice_item["grounding"]["skills_used"]

def test_compare_candidates_happy_path(clean_database_sandboxing):
    payload = {
        "ranking_id": "rank_001",
        "candidate_ids": ["CAND_0000001", "CAND_0000002"]
    }
    response = client.post("/api/v1/ai/compare", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["ranking_id"] == "rank_001"
    assert "Alice Green" in data["comparison"]
    assert "Bob Blue" in data["comparison"]
    assert "ranks higher than Bob Blue" in data["comparison"]
    assert "CAND_0000001" in data["grounding"]
    assert "CAND_0000002" in data["grounding"]
    assert data["grounding"]["CAND_0000001"]["skills_used"] == ["python", "fastapi", "postgresql"]
    assert data["grounding"]["CAND_0000002"]["missing_required_skills"] == ["postgresql"]

def test_shortlist_summary_happy_path(clean_database_sandboxing):
    payload = {"ranking_id": "rank_001"}
    response = client.post("/api/v1/ai/shortlist-summary", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["ranking_id"] == "rank_001"
    assert "evaluated 3 candidates" in data["summary"]
    assert "Alice Green" in data["summary"]
    assert "postgresql" in data["summary"]
    assert "fastapi" in data["summary"]
    assert "Warning: 1 candidate(s) have low parsing confidence" in data["summary"]
    assert set(data["grounding"]["candidate_ids"]) == {"CAND_0000001", "CAND_0000002", "CAND_0000003"}
    assert set(data["grounding"]["missing_required_skills"]) == {"fastapi", "postgresql"}

def test_ai_module_validation_errors(clean_database_sandboxing):
    # 1. Ranking not found (404)
    payload = {"ranking_id": "rank_not_exists", "candidate_id": "CAND_0000001"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RANKING_NOT_FOUND"

    # 2. Context not ready (400)
    payload = {"ranking_id": "rank_not_ready", "candidate_id": "CAND_0000001"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AI_CONTEXT_NOT_READY"

    # 3. Candidate not in ranking (404)
    payload = {"ranking_id": "rank_001", "candidate_id": "CAND_NOT_IN_RANKING"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CANDIDATE_NOT_FOUND"

    # 4. Incomplete profile in DB (422)
    # Register candidate in ranking but remove from candidates db
    _rankings_db["rank_001"]["candidates"].append({
        "candidate_id": "CAND_INCOMPLETE",
        "rank_position": 4,
        "fit_score": 0.1,
        "confidence_score": 0.1,
        "missing_required_skills": []
    })
    payload = {"ranking_id": "rank_001", "candidate_id": "CAND_INCOMPLETE"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AI_EVIDENCE_INCOMPLETE"

def test_provider_failure(clean_database_sandboxing):
    payload = {"ranking_id": "rank_provider_err", "candidate_id": "CAND_0000001"}
    response = client.post("/api/v1/ai/explanations", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_ERROR"
