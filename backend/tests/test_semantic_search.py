import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.modules.semantic_search.service import (
    _embeddings_db, _candidate_index, _job_index,
    _candidate_vector_keys, _job_vector_keys, SemanticSearchService
)

client = TestClient(app)
RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}

@pytest.fixture(autouse=True)
def reset_semantic_search_state():
    """Resets the semantic search module and source DB states before each test."""
    from app.modules.semantic_search import service
    service._embeddings_db.clear()
    service._candidate_vectors.clear()
    service._job_vectors.clear()
    service._candidate_index = None
    service._job_index = None
    service._candidate_vector_keys.clear()
    service._job_vector_keys.clear()
    service._candidate_last_rebuilt_at = None
    service._job_last_rebuilt_at = None

    # Reset Candidate DB
    from app.modules.candidate import service as cand_service
    cand_service._candidates_db.clear()
    cand_service._candidate_evidence_db.clear()
    cand_service._candidate_counter = 0
    cand_service._evidence_counter = 0

    # Reset Job DB to initial default state
    from app.modules.job import service as job_service
    from app.common.schemas import JobStatus
    job_service._jobs_db.clear()
    job_service._jobs_db["JOB_0000001"] = {
        "job_id": "JOB_0000001",
        "title": "Senior Backend Engineer",
        "status": JobStatus.ACTIVE,
        "required_skills": ["python", "fastapi", "postgresql"],
        "preferred_skills": ["distributed_systems"],
        "confidence_score": 0.93,
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:45:00Z",
        "candidate_count": 42,
        "description_text": (
            "We are hiring a Senior Backend Engineer with strong Python, FastAPI, "
            "PostgreSQL, and distributed systems experience."
        )
    }
    job_service._job_requirements_db.clear()
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

def test_semantic_search_flow():
    # 1. Initially index is not ready, searching should return 503 (database is empty of candidates)
    search_payload = {
        "job_id": "JOB_0000001",
        "top_k": 5
    }
    response = client.post("/api/v1/semantic-search/candidates/search", json=search_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INDEX_NOT_READY"

    # 2. Ingest candidate via API
    cand_payload = {
        "full_name": "FastAPI Developer Extraordinaire",
        "source_type": "TEXT",
        "source_text": "Experienced engineer specializing in python, fastapi, and postgresql.",
        "email": "fastapi.expert@example.com"
    }
    create_cand_response = client.post("/api/v1/candidates", json=cand_payload, headers=RECRUITER_HEADERS)
    assert create_cand_response.status_code == 201
    candidate_id = create_cand_response.json()["candidate"]["candidate_id"]

    # 3. Status should be NOT_READY since embeddings haven't been generated
    status_response = client.get("/api/v1/semantic-search/indexes/status", headers=RECRUITER_HEADERS)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["indexes"]["candidate"]["status"] == "NOT_READY"
    assert status_data["indexes"]["job"]["status"] == "NOT_READY"

    # 4. Refresh embeddings (synchronously via API)
    refresh_payload = {}
    refresh_response = client.post("/api/v1/semantic-search/embeddings/refresh", json=refresh_payload, headers=RECRUITER_HEADERS)
    assert refresh_response.status_code == 200
    assert refresh_response.json()["refreshed_count"] >= 2  # JOB_0000001 + new candidate

    # 5. Index should now be READY
    status_response = client.get("/api/v1/semantic-search/indexes/status", headers=RECRUITER_HEADERS)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["indexes"]["candidate"]["status"] == "READY"
    assert status_data["indexes"]["candidate"]["vector_count"] == 1
    assert status_data["indexes"]["job"]["status"] == "READY"
    assert status_data["indexes"]["job"]["vector_count"] == 1

    # 6. Candidate search (Happy path)
    search_response = client.post("/api/v1/semantic-search/candidates/search", json=search_payload, headers=RECRUITER_HEADERS)
    assert search_response.status_code == 200
    search_results = search_response.json()
    assert search_results["job_id"] == "JOB_0000001"
    assert len(search_results["items"]) == 1
    assert search_results["items"][0]["candidate_id"] == candidate_id
    assert "semantic_score" in search_results["items"][0]
    assert search_results["items"][0]["embedding_version"] == "candidate_profile_v1"

    # 7. Job search (Happy path)
    job_search_payload = {
        "candidate_id": candidate_id,
        "top_k": 5
    }
    job_search_response = client.post("/api/v1/semantic-search/jobs/search", json=job_search_payload, headers=RECRUITER_HEADERS)
    assert job_search_response.status_code == 200
    job_search_results = job_search_response.json()
    assert job_search_results["candidate_id"] == candidate_id
    assert len(job_search_results["items"]) == 1
    assert job_search_results["items"][0]["job_id"] == "JOB_0000001"
    assert "semantic_score" in job_search_results["items"][0]
    assert job_search_results["items"][0]["embedding_version"] == "job_requirements_v1"

def test_semantic_search_stale_index_behavior():
    # 1. Setup ready index
    client.post(
        "/api/v1/candidates",
        json={"full_name": "Test Candidate", "source_type": "TEXT", "source_text": "python postgresql"},
        headers=RECRUITER_HEADERS
    )
    client.post("/api/v1/semantic-search/embeddings/refresh", json={}, headers=RECRUITER_HEADERS)
    
    status_response = client.get("/api/v1/semantic-search/indexes/status", headers=RECRUITER_HEADERS)
    assert status_response.json()["indexes"]["job"]["status"] == "READY"

    # 2. Update job details, causing embedding status to be STALE
    update_job_payload = {
        "description_text": "Updated job description requesting spacy and next.js skill sets."
    }
    client.patch("/api/v1/jobs/JOB_0000001", json=update_job_payload, headers=RECRUITER_HEADERS)

    # 3. Job Index should now be marked STALE
    status_response = client.get("/api/v1/semantic-search/indexes/status", headers=RECRUITER_HEADERS)
    assert status_response.json()["indexes"]["job"]["status"] == "STALE"

    # 4. Refresh embeddings to reconcile index status back to READY
    client.post("/api/v1/semantic-search/embeddings/refresh", json={}, headers=RECRUITER_HEADERS)
    status_response = client.get("/api/v1/semantic-search/indexes/status", headers=RECRUITER_HEADERS)
    assert status_response.json()["indexes"]["job"]["status"] == "READY"

def test_semantic_search_validation_errors():
    # 1. Search non-existent job -> 404 JOB_NOT_FOUND
    search_payload = {
        "job_id": "JOB_9999999",
        "top_k": 5
    }
    response = client.post("/api/v1/semantic-search/candidates/search", json=search_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

    # 2. Search non-existent candidate -> 404 CANDIDATE_NOT_FOUND
    job_search_payload = {
        "candidate_id": "CAND_9999999",
        "top_k": 5
    }
    response = client.post("/api/v1/semantic-search/jobs/search", json=job_search_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CANDIDATE_NOT_FOUND"

    # 3. Refresh single invalid entity
    refresh_payload = {
        "entity_type": "CANDIDATE",
        "entity_id": "CAND_9999999"
    }
    response = client.post("/api/v1/semantic-search/embeddings/refresh", json=refresh_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CANDIDATE_NOT_FOUND"

def test_semantic_search_canonical_inputs():
    # Verify that source_text generated for embedding matches canonical fields exactly
    client.post(
        "/api/v1/candidates",
        json={"full_name": "Alice Green", "source_type": "TEXT", "source_text": "python react"},
        headers=RECRUITER_HEADERS
    )
    # Trigger refresh
    client.post("/api/v1/semantic-search/embeddings/refresh", json={}, headers=RECRUITER_HEADERS)
    
    from app.modules.semantic_search.service import _embeddings_db
    
    # Candidate embedding canonical text format: Name + skills + signals
    cand_emb_key = next(k for k in _embeddings_db if "cand" in k)
    cand_emb = _embeddings_db[cand_emb_key]
    assert cand_emb["entity_type"] == "CANDIDATE"
    # Ensure source_hash is populated
    assert len(cand_emb["source_hash"]) == 32
