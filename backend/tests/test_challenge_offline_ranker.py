import csv
import json

from app.challenge.offline_ranker import iter_candidate_records, rank_candidates, run_submission


def _candidate(candidate_id, title, years, skills, signals, summary=""):
    return {
        "candidate_id": candidate_id,
        "profile": {
            "anonymized_name": f"Candidate {candidate_id}",
            "headline": title,
            "summary": summary,
            "location": "Pune, India",
            "country": "India",
            "years_of_experience": years,
            "current_title": title,
            "current_company": "Example AI",
            "current_company_size": "51-200",
            "current_industry": "Artificial Intelligence",
        },
        "career_history": [
            {
                "company": "Example AI",
                "title": title,
                "duration_months": int(years * 12),
                "is_current": True,
                "industry": "Artificial Intelligence",
                "description": summary,
            }
        ],
        "education": [],
        "skills": skills,
        "redrob_signals": signals,
    }


def test_offline_ranker_prioritizes_ai_retrieval_candidate():
    strong = _candidate(
        "CAND_0000002",
        "Senior AI Engineer",
        6.5,
        [
            {"name": "Python", "proficiency": "expert", "endorsements": 20, "duration_months": 72},
            {"name": "LLM fine-tuning", "proficiency": "advanced", "endorsements": 12, "duration_months": 24},
            {"name": "Embeddings", "proficiency": "expert", "endorsements": 18, "duration_months": 36},
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 8, "duration_months": 18},
            {"name": "Ranking", "proficiency": "advanced", "endorsements": 10, "duration_months": 30},
        ],
        {
            "profile_completeness_score": 96,
            "last_active_date": "2026-06-18",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.82,
            "avg_response_time_hours": 8,
            "notice_period_days": 30,
            "saved_by_recruiters_30d": 7,
            "search_appearance_30d": 75,
            "profile_views_received_30d": 60,
            "github_activity_score": 88,
            "interview_completion_rate": 0.95,
            "offer_acceptance_rate": 0.8,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
            "willing_to_relocate": True,
            "preferred_work_mode": "hybrid",
            "skill_assessment_scores": {"Machine Learning": 91, "Python": 94},
        },
        "Shipped production semantic search, embeddings, hybrid retrieval, ranking, and LLM reranking systems for recruiter workflows.",
    )
    weak = _candidate(
        "CAND_0000001",
        "Research Intern",
        1.2,
        [{"name": "Excel", "proficiency": "intermediate", "endorsements": 2, "duration_months": 12}],
        {
            "profile_completeness_score": 45,
            "last_active_date": "2025-01-01",
            "open_to_work_flag": False,
            "recruiter_response_rate": 0.1,
            "avg_response_time_hours": 120,
            "notice_period_days": 120,
            "verified_email": True,
        },
        "Academic research exposure without production deployment.",
    )

    ranked = rank_candidates([weak, strong], top_k=2)

    assert ranked[0].candidate_id == "CAND_0000002"
    assert ranked[0].score > ranked[1].score
    assert "embeddings" in ranked[0].reasoning.lower()


def test_run_submission_writes_exact_organizer_columns(tmp_path):
    candidates_path = tmp_path / "candidates.jsonl"
    output_path = tmp_path / "submission.csv"
    records = [
        _candidate(
            "CAND_0000003",
            "Machine Learning Engineer",
            5.5,
            [{"name": "Python", "proficiency": "advanced", "endorsements": 12, "duration_months": 36}],
            {"profile_completeness_score": 90, "open_to_work_flag": True, "last_active_date": "2026-06-12"},
            "Built production machine learning APIs.",
        ),
        _candidate(
            "CAND_0000004",
            "Backend Engineer",
            4.0,
            [{"name": "FastAPI", "proficiency": "advanced", "endorsements": 7, "duration_months": 30}],
            {"profile_completeness_score": 80, "open_to_work_flag": True, "last_active_date": "2026-06-10"},
            "Built backend APIs.",
        ),
    ]
    with open(candidates_path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    rows = run_submission(candidates_path, output_path, top_k=2, strict=True)

    assert [row.candidate_id for row in rows] == ["CAND_0000003", "CAND_0000004"]
    with open(output_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        csv_rows = list(reader)

    assert reader.fieldnames == ["candidate_id", "rank", "score", "reasoning"]
    assert csv_rows[0]["candidate_id"] == "CAND_0000003"
    assert csv_rows[0]["rank"] == "1"
    assert float(csv_rows[0]["score"]) >= float(csv_rows[1]["score"])
    assert csv_rows[0]["reasoning"]


def test_iter_candidate_records_supports_json_array(tmp_path):
    candidates_path = tmp_path / "sample_candidates.json"
    records = [
        _candidate(
            "CAND_0000005",
            "AI Engineer",
            6.0,
            [{"name": "NLP", "proficiency": "advanced"}],
            {"profile_completeness_score": 88},
        )
    ]
    candidates_path.write_text(json.dumps(records), encoding="utf-8")

    parsed = list(iter_candidate_records(candidates_path))

    assert parsed[0]["candidate_id"] == "CAND_0000005"
