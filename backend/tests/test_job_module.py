from fastapi.testclient import TestClient

from app.main import app
from app.common.schemas import JobCreate, SourceType
from app.common.errors import HireSenseException
from app.modules.job import service as job_service


client = TestClient(app)
RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}


def test_job_ingestion_extracts_normalized_evidence_backed_requirements():
    payload = {
        "title": "Platform Engineer",
        "source_type": "TEXT",
        "description_text": (
            "Required skills: Python 3, Fast API, and Postgres. "
            "Responsibilities: build and maintain internal APIs. "
            "Preferred skills: distributed systems and AWS."
        ),
        "location": "Bengaluru",
        "employment_type": "FULL_TIME",
    }

    response = client.post("/api/v1/jobs", json=payload, headers=RECRUITER_HEADERS)

    assert response.status_code == 201
    job = response.json()["job"]
    assert job["required_skills"] == ["python", "fastapi", "postgresql"]
    assert job["preferred_skills"] == ["aws", "distributed_systems"]
    assert job["confidence_score"] >= 0.85

    requirements_response = client.get(
        f"/api/v1/jobs/{job['job_id']}/requirements",
        headers=RECRUITER_HEADERS,
    )
    assert requirements_response.status_code == 200
    requirements = requirements_response.json()["job_requirements"]
    evidence = requirements["requirement_evidence"]
    required_evidence = [item for item in evidence if item["requirement_type"] == "REQUIRED_SKILL"]

    assert {item["canonical_value"] for item in required_evidence} == {"python", "fastapi", "postgresql"}
    assert all(item["source_text"] for item in required_evidence)
    assert all(item["source_span_start"] is not None for item in required_evidence)
    assert requirements["embedding_metadata"]["embedding_version"] == "job_requirements_v1"


def test_job_description_without_requirement_evidence_does_not_invent_required_skills():
    payload = {
        "title": "General Role",
        "source_type": "TEXT",
        "description_text": (
            "This role supports team coordination and stakeholder communication. "
            "The hiring manager will add technical requirements later."
        ),
    }

    response = client.post("/api/v1/jobs", json=payload, headers=RECRUITER_HEADERS)

    assert response.status_code == 201
    job = response.json()["job"]
    assert job["required_skills"] == []
    assert job["preferred_skills"] == []
    assert job["confidence_score"] < 0.85


def test_job_ingestion_rejects_malformed_description():
    payload = {
        "title": "Backend Engineer",
        "source_type": "TEXT",
        "description_text": "Python",
    }

    response = client.post("/api/v1/jobs", json=payload, headers=RECRUITER_HEADERS)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert "description_text" in response.json()["error"]["details"]["field"]


def test_job_storage_failure_returns_documented_error(monkeypatch):
    def fail_store(job_id, job_record, requirement_evidence):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(job_service, "_store_job_record", fail_store)
    payload = JobCreate(
        title="Backend Engineer",
        source_type=SourceType.TEXT,
        description_text="Required skills: Python and FastAPI. Responsibilities: build APIs.",
    )

    try:
        job_service.JobService.create_job(payload)
    except HireSenseException as exc:
        assert exc.status_code == 503
        assert exc.code == "JOB_STORAGE_FAILED"
        assert exc.details["job_id"].startswith("JOB_")
    else:
        raise AssertionError("Expected JOB_STORAGE_FAILED")


def test_skill_aliases_normalize_to_canonical_values():
    payload = {
        "title": "API Engineer",
        "source_type": "TEXT",
        "description_text": (
            "Must have Python3, Fast API, PostgreSQL, ReactJS, NextJS, and containerization experience."
        ),
    }

    response = client.post("/api/v1/jobs", json=payload, headers=RECRUITER_HEADERS)

    assert response.status_code == 201
    required_skills = response.json()["job"]["required_skills"]
    assert required_skills == ["python", "fastapi", "postgresql", "react", "next.js", "docker"]


def test_job_update_refreshes_parsing_and_versions():
    create_response = client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend Engineer",
            "source_type": "TEXT",
            "description_text": "Required skills: Python and FastAPI.",
        },
        headers=RECRUITER_HEADERS,
    )

    assert create_response.status_code == 201
    job_id = create_response.json()["job"]["job_id"]

    update_response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={
            "description_text": (
                "Required skills: Python, FastAPI, and PostgreSQL. "
                "Preferred skills: AWS."
            ),
            "location": "Remote",
        },
        headers=RECRUITER_HEADERS,
    )

    assert update_response.status_code == 200
    job = update_response.json()["job"]
    assert job["required_skills"] == ["python", "fastapi", "postgresql"]
    assert job["preferred_skills"] == ["aws"]
    assert job["location"] == "Remote"
    assert job["requirement_version"] >= 2


def test_job_reprocess_reparses_existing_description():
    create_response = client.post(
        "/api/v1/jobs",
        json={
            "title": "Data Engineer",
            "source_type": "TEXT",
            "description_text": "Required skills: Python and SQL.",
        },
        headers=RECRUITER_HEADERS,
    )

    assert create_response.status_code == 201
    job = create_response.json()["job"]
    job_id = job["job_id"]

    job_service._jobs_db[job_id]["description_text"] = (
        "Required skills: Python, SQL, and FastAPI. Preferred skills: Docker."
    )

    reprocess_response = client.post(
        f"/api/v1/jobs/{job_id}/reprocess",
        headers=RECRUITER_HEADERS,
    )

    assert reprocess_response.status_code == 200
    refreshed = reprocess_response.json()["job"]
    assert refreshed["required_skills"] == ["python", "fastapi"]
    assert refreshed["preferred_skills"] == ["docker"]
    assert refreshed["requirement_version"] >= 2


def test_job_listing_returns_next_page_token():
    first_job = client.post(
        "/api/v1/jobs",
        json={
            "title": "Search Engineer",
            "source_type": "TEXT",
            "description_text": "Required skills: Python and FAISS.",
        },
        headers=RECRUITER_HEADERS,
    )
    second_job = client.post(
        "/api/v1/jobs",
        json={
            "title": "ML Engineer",
            "source_type": "TEXT",
            "description_text": "Required skills: Python and spaCy.",
        },
        headers=RECRUITER_HEADERS,
    )

    assert first_job.status_code == 201
    assert second_job.status_code == 201

    list_response = client.get("/api/v1/jobs?limit=1", headers=RECRUITER_HEADERS)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload["items"]) == 1
    assert payload["next_page_token"]

    next_page_response = client.get(
        f"/api/v1/jobs?limit=1&page_token={payload['next_page_token']}",
        headers=RECRUITER_HEADERS,
    )
    assert next_page_response.status_code == 200
    assert len(next_page_response.json()["items"]) == 1


def test_job_listing_filters_by_status():
    response = client.get("/api/v1/jobs?status=ACTIVE", headers=RECRUITER_HEADERS)

    assert response.status_code == 200
    assert all(item["status"] == "ACTIVE" for item in response.json()["items"])
