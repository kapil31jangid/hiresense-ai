import pytest
from fastapi.testclient import TestClient
import os
import io

from app.main import app
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.modules.ranking.service import _rankings_db

client = TestClient(app)

# Helper headers
RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}
ADMIN_HEADERS = {"Authorization": "Bearer admin_token"}

def test_health_endpoints():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "ok"
    assert "request_id" in health_data

    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "request_id" in data
    assert "postgresql" in data["dependencies"]

def test_auth_me():
    # Unauthenticated
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    error_data = response.json()
    assert "request_id" in error_data
    assert error_data["error"]["code"] == "UNAUTHORIZED"

    # Authenticated recruiter
    response = client.get("/api/v1/me", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "RECRUITER"
    assert data["user"]["user_id"] == "user_recruiter_001"

    # Authenticated admin
    response = client.get("/api/v1/me", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "ADMIN"

    # Invalid token should be rejected
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer not_a_real_token"})
    assert response.status_code == 401
    error_data = response.json()
    assert error_data["error"]["code"] == "UNAUTHORIZED"

def test_validation_errors():
    # Missing required body field for Job Creation
    response = client.post("/api/v1/jobs", json={}, headers=RECRUITER_HEADERS)
    assert response.status_code == 400
    error_data = response.json()
    assert error_data["error"]["code"] == "INVALID_REQUEST"
    assert "required" in error_data["error"]["message"].lower()

    # Invalid query parameters
    response = client.get("/api/v1/jobs?limit=invalid", headers=RECRUITER_HEADERS)
    assert response.status_code == 400
    error_data = response.json()
    assert error_data["error"]["code"] == "INVALID_QUERY"

def test_job_flow():
    # Create a job
    job_payload = {
        "title": "React Frontend Developer",
        "source_type": "TEXT",
        "description_text": "Looking for someone with React, Next.js, and Docker experience.",
        "location": "Remote",
        "employment_type": "FULL_TIME"
    }
    response = client.post("/api/v1/jobs", json=job_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    res_data = response.json()
    job = res_data["job"]
    assert job["title"] == "React Frontend Developer"
    # Should dynamically extract skills
    assert "react" in job["required_skills"]
    assert "next.js" in job["required_skills"]
    assert "docker" in job["required_skills"]
    job_id = job["job_id"]

    # Get job detail
    response = client.get(f"/api/v1/jobs/{job_id}", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    assert response.json()["job"]["job_id"] == job_id

    # List jobs
    response = client.get("/api/v1/jobs", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 2
    assert any(item["job_id"] == job_id for item in items)

def test_candidate_flow():
    # Create a candidate via JSON
    cand_payload = {
        "full_name": "John Doe",
        "source_type": "TEXT",
        "email": "john.doe@example.com"
    }
    response = client.post("/api/v1/candidates", json=cand_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    cand = response.json()["candidate"]
    assert cand["full_name"] == "John Doe"
    assert "candidate_id" in cand

    # Create candidate via Multipart File upload
    file_content = b"Candidate Resume content"
    response = client.post(
        "/api/v1/candidates/upload",
        data={"full_name": "Jane Miller", "email": "jane@example.com"},
        files={"file": ("jane_react_resume.pdf", file_content, "application/pdf")},
        headers=RECRUITER_HEADERS
    )
    assert response.status_code == 201
    cand_upload = response.json()["candidate"]
    assert cand_upload["full_name"] == "Jane Miller"
    # File name includes react, should extract react skill
    assert "react" in cand_upload["normalized_skills"]

def test_ranking_and_export():
    # 1. Ensure clean base state or fetch existing JOB_0000001 and CAND_0000001
    assert "JOB_0000001" in _jobs_db
    assert "CAND_0000001" in _candidates_db

    # 2. Run ranking sync pipeline (requires admin)
    pipeline_payload = {
        "job_id": "JOB_0000001",
        "trigger_mode": "MANUAL"
    }
    # Should fail if recruiter
    response = client.post("/api/v1/pipeline/runs/ranking-sync", json=pipeline_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 401
    
    # Should pass if admin
    response = client.post("/api/v1/pipeline/runs/ranking-sync", json=pipeline_payload, headers=ADMIN_HEADERS)
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"

    # 3. Create ranking run
    ranking_payload = {
        "job_id": "JOB_0000001",
        "candidate_ids": ["CAND_0000001"],
        "ranking_strategy": "HYBRID_WEIGHTED_V1"
    }
    response = client.post("/api/v1/rankings", json=ranking_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    ranking_id = response.json()["ranking"]["ranking_id"]

    # 4. Get ranking candidates
    response = client.get(f"/api/v1/rankings/{ranking_id}/candidates", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["candidate_id"] == "CAND_0000001"
    assert "fit_score" in items[0]
    assert "confidence_score" in items[0]

    # 5. Export shortlist to CSV
    response = client.get(f"/api/v1/rankings/{ranking_id}/export/csv", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    export_data = response.json()
    assert export_data["ranking_id"] == ranking_id
    assert "download_url" in export_data

    # 6. Verify export uses stored ranking results and download serves correct CSV content
    download_url = export_data["download_url"]
    response = client.get(download_url)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    csv_content = response.text
    # Should contain headers and candidate details
    assert "rank_position" in csv_content
    assert "CAND_0000001" in csv_content

def test_semantic_search():
    search_payload = {
        "job_id": "JOB_0000001",
        "top_k": 5
    }
    response = client.post("/api/v1/semantic-search/candidates/search", json=search_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "JOB_0000001"
    assert "items" in data
    assert len(data["items"]) > 0
    assert "semantic_score" in data["items"][0]

def test_ai_explanations():
    # AI explanation for existing ranking
    explanation_payload = {
        "ranking_id": "rank_001",
        "candidate_id": "CAND_0000001"
    }
    response = client.post("/api/v1/ai/explanations", json=explanation_payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["ranking_id"] == "rank_001"
    assert data["candidate_id"] == "CAND_0000001"
    assert "explanation" in data
    assert "grounding" in data
    assert "skills_used" in data["grounding"]

def test_analytics_and_alerts():
    # Alerts
    response = client.get("/api/v1/alerts", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    assert "items" in response.json()
    assert len(response.json()["items"]) > 0

    # Analytics dashboard
    response = client.get("/api/v1/analytics/dashboard", headers=RECRUITER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "analytics_last_updated_at" in data
    assert data["freshness_status"] == "FRESH"
    assert data["summary"]["active_jobs"] > 0
