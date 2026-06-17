import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
RECRUITER_HEADERS = {"Authorization": "Bearer recruiter_token"}

def test_candidate_creation_json():
    payload = {
        "full_name": "Devin AI Developer",
        "source_type": "TEXT",
        "email": "devin@example.com",
        "source_text": (
            "Resume profile for Devin AI Developer. Contact: devin@example.com. "
            "Education: Bachelor of Science in Computer Science, University of Technology, 2018. "
            "Experience: Worked for 5.4 years as a Software Engineer. "
            "Technical Skills: Proficient in Python, FastAPI, PostgreSQL. "
            "Professional signals: Strong history of collaboration and ownership."
        )
    }
    response = client.post("/api/v1/candidates", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 201
    
    data = response.json()
    assert "request_id" in data
    
    candidate = data["candidate"]
    assert candidate["full_name"] == "Devin AI Developer"
    assert "candidate_id" in candidate
    assert candidate["years_of_experience"] == 5.4
    assert candidate["confidence_score"] >= 0.85
    assert candidate["parsing_status"] == "COMPLETED"
    
    # Verify challenge schema fields
    assert "profile" in candidate
    assert candidate["profile"]["email"] == "devin@example.com"
    assert "career_history" in candidate
    assert len(candidate["career_history"]) > 0
    assert "education" in candidate
    assert "skills" in candidate
    assert "redrob_signals" in candidate
    assert "collaboration" in candidate["redrob_signals"]

def test_candidate_creation_file_and_normalization():
    file_content = (
        b"Resume profile for Jane Doe. Contact: jane.doe@example.com.\n"
        b"Education: Bachelor of Science in Computer Science, University of Technology, 2018.\n"
        b"Experience: Worked for 4.0 years as a Software Engineer.\n"
        b"Technical Skills: Proficient in React, PostgreSQL, and FastAPI.\n"
        b"Professional signals: Strong history of ownership and collaboration."
    )
    response = client.post(
        "/api/v1/candidates/upload",
        data={"full_name": "Jane Doe", "email": "jane.doe@example.com"},
        files={"file": ("jane_react_postgres_resume.pdf", file_content, "application/pdf")},
        headers=RECRUITER_HEADERS
    )
    assert response.status_code == 201
    
    candidate = response.json()["candidate"]
    assert candidate["full_name"] == "Jane Doe"
    # Should normalize react and postgresql aliases
    assert "react" in candidate["normalized_skills"]
    assert "postgresql" in candidate["normalized_skills"]
    assert "fastapi" in candidate["normalized_skills"]
    assert "ownership" in candidate["redrob_signals"]
    assert candidate["parsing_status"] == "COMPLETED"

def test_candidate_details_and_evidence():
    # Ingest a candidate
    payload = {
        "full_name": "Evidence Test",
        "source_type": "TEXT",
        "email": "evidence@example.com",
        "source_text": (
            "Resume profile for Evidence Test. Contact: evidence@example.com. "
            "Education: Bachelor of Science in Computer Science, University of Technology, 2018. "
            "Experience: Worked for 5.4 years as a Software Engineer. "
            "Technical Skills: Proficient in Python and PostgreSQL. "
            "Professional signals: Strong history of mentorship."
        )
    }
    create_response = client.post("/api/v1/candidates", json=payload, headers=RECRUITER_HEADERS)
    candidate_id = create_response.json()["candidate"]["candidate_id"]
    
    # Get details
    detail_response = client.get(f"/api/v1/candidates/{candidate_id}", headers=RECRUITER_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()["candidate"]
    assert detail["full_name"] == "Evidence Test"
    assert "profile" in detail
    assert "career_history" in detail
    assert detail["parsing_status"] == "COMPLETED"
    
    # Get evidence
    evidence_response = client.get(f"/api/v1/candidates/{candidate_id}/resume-evidence", headers=RECRUITER_HEADERS)
    assert evidence_response.status_code == 200
    ev_data = evidence_response.json()
    assert ev_data["candidate_id"] == candidate_id
    assert "request_id" in ev_data
    assert len(ev_data["evidence"]) > 0
    
    for ev in ev_data["evidence"]:
        assert "source_span_start" in ev
        assert "source_span_end" in ev
        assert "evidence_type" in ev
        assert "canonical_value" in ev

def test_candidate_update_and_reprocess():
    # Ingest
    payload = {
        "full_name": "Reprocess Test",
        "source_type": "TEXT",
        "source_text": (
            "Resume profile for Reprocess Test. Contact: reprocess@example.com. "
            "Education: Bachelor of Science in Computer Science, University of Technology, 2018. "
            "Experience: Worked for 3.5 years as a Software Engineer. "
            "Technical Skills: Proficient in Python and FastAPI. "
            "Professional signals: Strong history of ownership."
        )
    }
    create_response = client.post("/api/v1/candidates", json=payload, headers=RECRUITER_HEADERS)
    candidate_id = create_response.json()["candidate"]["candidate_id"]
    
    # PATCH candidate profile
    update_payload = {
        "full_name": "Updated Reprocess Test",
        "years_of_experience": 8.5,
        "redrob_signals": ["ownership", "mentorship"]
    }
    patch_response = client.patch(f"/api/v1/candidates/{candidate_id}", json=update_payload, headers=RECRUITER_HEADERS)
    assert patch_response.status_code == 200
    updated = patch_response.json()["candidate"]
    assert updated["full_name"] == "Updated Reprocess Test"
    assert updated["years_of_experience"] == 8.5
    assert "mentorship" in updated["redrob_signals"]
    assert updated["embedding_metadata"]["status"] == "STALE"
    assert updated["parsing_status"] in {"COMPLETED", "PARTIAL"}
    
    # Reprocess candidate
    reprocess_response = client.post(f"/api/v1/candidates/{candidate_id}/reprocess", headers=RECRUITER_HEADERS)
    assert reprocess_response.status_code == 200
    reprocessed = reprocess_response.json()["candidate"]
    # Reprocessing should restore source-backed parsing values
    assert reprocessed["years_of_experience"] == 3.5
    assert reprocessed["embedding_metadata"]["status"] == "STALE"

def test_validation_and_not_found():
    # Validation error for blank name
    payload = {
        "full_name": "   ",
        "source_type": "TEXT"
    }
    response = client.post("/api/v1/candidates", json=payload, headers=RECRUITER_HEADERS)
    assert response.status_code == 400
    error_data = response.json()
    assert error_data["error"]["code"] == "INVALID_REQUEST"
    assert "request_id" in error_data
    
    # Not found details check
    response = client.get("/api/v1/candidates/CAND_9999999", headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error"]["code"] == "CANDIDATE_NOT_FOUND"
    
    # Not found evidence check
    response = client.get("/api/v1/candidates/CAND_9999999/resume-evidence", headers=RECRUITER_HEADERS)
    assert response.status_code == 404
    
    # Not found reprocess check
    response = client.post("/api/v1/candidates/CAND_9999999/reprocess", headers=RECRUITER_HEADERS)
    assert response.status_code == 404


def test_candidate_listing_returns_next_page_token():
    for idx in range(2):
        response = client.post(
            "/api/v1/candidates",
            json={
                "full_name": f"Paging Candidate {idx}",
                "source_type": "TEXT",
                "email": f"paging{idx}@example.com",
                "source_text": (
                    f"Resume profile for Paging Candidate {idx}. "
                    f"Education: Bachelor of Science in Computer Science, University of Technology, 2018. "
                    f"Experience: Worked for 2.0 years as a Software Engineer. "
                    f"Technical Skills: Proficient in Python and FastAPI. "
                    f"Professional signals: Strong history of collaboration."
                )
            },
            headers=RECRUITER_HEADERS
        )
        assert response.status_code == 201

    list_response = client.get("/api/v1/candidates?limit=1", headers=RECRUITER_HEADERS)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload["items"]) == 1
    assert payload["next_page_token"]

    next_page_response = client.get(
        f"/api/v1/candidates?limit=1&page_token={payload['next_page_token']}",
        headers=RECRUITER_HEADERS
    )
    assert next_page_response.status_code == 200
    assert len(next_page_response.json()["items"]) == 1
