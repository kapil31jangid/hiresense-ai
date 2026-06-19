"""
Demo data seeder for HireSense AI.

Populates in-memory stores with realistic demo data on startup so the app
works immediately without requiring any manual data entry.

This seeder is idempotent — it only seeds when the stores are empty.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_candidates_jsonl() -> list[dict]:
    """Load candidates from demo_data/candidates.jsonl relative to this file."""
    here = os.path.dirname(os.path.abspath(__file__))
    jsonl_path = os.path.join(here, "..", "demo_data", "candidates.jsonl")
    jsonl_path = os.path.normpath(jsonl_path)
    records = []
    if not os.path.isfile(jsonl_path):
        return records
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def seed_demo_data() -> None:
    """Seed demo data into in-memory stores if they are empty."""
    from app.modules.job import service as job_service
    from app.modules.candidate import service as candidate_service
    from app.modules.ranking import service as ranking_service
    from app.modules.alerts import service as alerts_service
    from app.common.schemas import JobStatus, RankingStatus, AlertStatus, AlertSeverity

    # Skip seeding if data already exists
    if len(job_service._jobs_db) > 0 or len(candidate_service._candidates_db) > 0:
        return

    now = _now()

    # ── JOBS ──────────────────────────────────────────────────────────────────
    # Three demo jobs matching the UI screenshot progression (JOB_0000001..3)

    job_service._jobs_db["JOB_0000001"] = {
        "job_id": "JOB_0000001",
        "title": "Senior AI Engineer – Embeddings & Ranking",
        "description_text": (
            "We need a Senior AI Engineer with strong expertise in Python, FastAPI, FAISS, "
            "and NLP. Experience with embeddings, LLM reranking, and production ML systems required. "
            "Preferred: distributed systems, spacy."
        ),
        "status": JobStatus.ACTIVE,
        "location": "Pune, India",
        "employment_type": "Full-time",
        "required_skills": ["python", "fastapi", "faiss", "nlp"],
        "preferred_skills": ["distributed_systems", "spacy"],
        "confidence_score": 0.92,
        "created_at": now,
        "updated_at": now,
        "candidate_count": 6,
        "role_intelligence": {"responsibilities": [], "qualifications": [], "requirement_count": 6},
        "embedding_metadata": {"status": "READY", "embedding_version": "job_requirements_v1"},
    }
    job_service._job_requirements_db["JOB_0000001"] = [
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "python", "source_text": "strong expertise in Python", "source_span_start": 40, "source_span_end": 67, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "fastapi", "source_text": "Python, FastAPI, FAISS", "source_span_start": 48, "source_span_end": 77, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "faiss", "source_text": "FastAPI, FAISS, and NLP", "source_span_start": 56, "source_span_end": 85, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "nlp", "source_text": "FAISS, and NLP", "source_span_start": 66, "source_span_end": 87, "confidence_score": 0.95},
        {"requirement_type": "PREFERRED_SKILL", "canonical_value": "distributed_systems", "source_text": "Preferred: distributed systems", "source_span_start": 140, "source_span_end": 170, "confidence_score": 0.88},
        {"requirement_type": "PREFERRED_SKILL", "canonical_value": "spacy", "source_text": "distributed systems, spacy", "source_span_start": 160, "source_span_end": 186, "confidence_score": 0.88},
    ]

    job_service._jobs_db["JOB_0000002"] = {
        "job_id": "JOB_0000002",
        "title": "Backend Platform Engineer",
        "description_text": (
            "Looking for a Backend Platform Engineer with expertise in Python, FastAPI, PostgreSQL, "
            "Docker, and distributed systems. Preferred: AWS, Kafka."
        ),
        "status": JobStatus.ACTIVE,
        "location": "Bengaluru, India",
        "employment_type": "Full-time",
        "required_skills": ["python", "fastapi", "postgresql", "docker"],
        "preferred_skills": ["aws", "distributed_systems"],
        "confidence_score": 0.90,
        "created_at": now,
        "updated_at": now,
        "candidate_count": 6,
        "role_intelligence": {"responsibilities": [], "qualifications": [], "requirement_count": 6},
        "embedding_metadata": {"status": "READY", "embedding_version": "job_requirements_v1"},
    }
    job_service._job_requirements_db["JOB_0000002"] = [
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "python", "source_text": "expertise in Python", "source_span_start": 50, "source_span_end": 70, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "fastapi", "source_text": "Python, FastAPI, PostgreSQL", "source_span_start": 58, "source_span_end": 85, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "postgresql", "source_text": "FastAPI, PostgreSQL, Docker", "source_span_start": 66, "source_span_end": 93, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "docker", "source_text": "PostgreSQL, Docker", "source_span_start": 78, "source_span_end": 96, "confidence_score": 0.95},
    ]

    job_service._jobs_db["JOB_0000003"] = {
        "job_id": "JOB_0000003",
        "title": "Full-Stack Engineer – React & Next.js",
        "description_text": (
            "We are looking for a Full-Stack Engineer with strong experience in React, Next.js, "
            "Python, and FastAPI. Required skills: react, next.js, python, fastapi. "
            "Preferred: docker, aws."
        ),
        "status": JobStatus.ACTIVE,
        "location": "Remote",
        "employment_type": "Full-time",
        "required_skills": ["react", "next.js", "python", "fastapi"],
        "preferred_skills": ["docker", "aws"],
        "confidence_score": 0.88,
        "created_at": now,
        "updated_at": now,
        "candidate_count": 5,
        "role_intelligence": {"responsibilities": [], "qualifications": [], "requirement_count": 5},
        "embedding_metadata": {"status": "READY", "embedding_version": "job_requirements_v1"},
    }
    job_service._job_requirements_db["JOB_0000003"] = [
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "react", "source_text": "strong experience in React", "source_span_start": 55, "source_span_end": 81, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "next.js", "source_text": "React, Next.js, Python", "source_span_start": 63, "source_span_end": 85, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "python", "source_text": "Next.js, Python, and FastAPI", "source_span_start": 72, "source_span_end": 100, "confidence_score": 0.95},
        {"requirement_type": "REQUIRED_SKILL", "canonical_value": "fastapi", "source_text": "Python, and FastAPI", "source_span_start": 82, "source_span_end": 101, "confidence_score": 0.95},
    ]

    job_service._job_counter = 3

    # ── CANDIDATES ────────────────────────────────────────────────────────────
    # Load from demo_data/candidates.jsonl + map to internal IDs CAND_0000001..N

    raw_candidates = _load_candidates_jsonl()

    # Skill aliases that the system recognizes
    _SKILL_MAP = {
        "Python": "python",
        "FastAPI": "fastapi",
        "FAISS": "faiss",
        "NLP": "nlp",
        "Natural Language Processing": "nlp",
        "Embeddings": "faiss",
        "Ranking": "faiss",
        "React": "react",
        "Next.js": "next.js",
        "Docker": "docker",
        "AWS": "aws",
        "GCP": "aws",
        "Machine Learning": "machine_learning",
        "Kafka": "distributed_systems",
        "spaCy": "spacy",
        "Transformers": "nlp",
        "PostgreSQL": "postgresql",
    }

    def _normalize_skills(raw_skills: list) -> list[str]:
        normalized = []
        for s in raw_skills or []:
            name = s.get("name", "") if isinstance(s, dict) else str(s)
            mapped = _SKILL_MAP.get(name, name.lower().replace(" ", "_"))
            if mapped not in normalized:
                normalized.append(mapped)
        return normalized

    candidate_id_map: dict[str, str] = {}
    ev_counter = 0

    for idx, raw in enumerate(raw_candidates, start=1):
        cand_id = f"CAND_{idx:07d}"
        orig_id = raw.get("candidate_id", cand_id)
        candidate_id_map[orig_id] = cand_id

        profile = raw.get("profile", {})
        skills_raw = raw.get("skills", [])
        career_history = raw.get("career_history", [])
        education = raw.get("education", [])
        redrob_signals_raw = raw.get("redrob_signals", {})

        normalized_skills = _normalize_skills(skills_raw)
        years_exp = profile.get("years_of_experience", 0.0)

        # Confidence: rich profile → high, sparse → lower
        completeness = redrob_signals_raw.get("profile_completeness_score", 70) if isinstance(redrob_signals_raw, dict) else 70
        confidence = round(min(0.95, max(0.25, completeness / 100 * 0.9 + 0.1)), 2)
        parsing_status = "COMPLETED" if career_history else "PARTIAL"

        # Build redrob_signals list
        redrob_signals: list[str] = []
        if isinstance(redrob_signals_raw, dict):
            if redrob_signals_raw.get("open_to_work_flag"):
                redrob_signals.append("open_to_work")
            if redrob_signals_raw.get("willing_to_relocate"):
                redrob_signals.append("willing_to_relocate")
            if redrob_signals_raw.get("verified_email"):
                redrob_signals.append("verified_email")

        cand_record = {
            "candidate_id": cand_id,
            "full_name": profile.get("anonymized_name", f"Candidate {idx}"),
            "normalized_skills": normalized_skills,
            "years_of_experience": years_exp,
            "confidence_score": confidence,
            "parsing_status": parsing_status,
            "created_at": now,
            "updated_at": now,
            "source_type": "JSON",
            "source_file_name": None,
            "source_text": profile.get("summary", ""),
            "source_data": raw,
            "profile": {
                "full_name": profile.get("anonymized_name", f"Candidate {idx}"),
                "headline": profile.get("headline", ""),
                "summary": profile.get("summary", ""),
                "location": profile.get("location", ""),
                "email": f"candidate{idx}@demo.hiresense.ai",
                "phone": None,
                "years_of_experience": years_exp,
                "current_title": profile.get("current_title", ""),
                "current_company": profile.get("current_company", ""),
            },
            "career_history": career_history,
            "education": education,
            "skills": normalized_skills,
            "redrob_signals": redrob_signals,
            "behavioral_signals": redrob_signals,
            "embedding_metadata": {
                "entity_type": "CANDIDATE",
                "entity_id": cand_id,
                "embedding_version": "candidate_profile_v1",
                "status": "READY",
                "source_text": profile.get("summary", ""),
            },
        }
        candidate_service._candidates_db[cand_id] = cand_record

        # Evidence records
        evidence = []
        for skill in normalized_skills:
            ev_counter += 1
            evidence.append({
                "candidate_experience_evidence_id": f"ev_{ev_counter:07d}",
                "candidate_id": cand_id,
                "evidence_type": "SKILL",
                "canonical_value": skill,
                "source_text": skill,
                "source_span_start": None,
                "source_span_end": None,
                "created_at": now,
            })
        candidate_service._candidate_evidence_db[cand_id] = evidence

    candidate_service._candidate_counter = len(raw_candidates)
    candidate_service._evidence_counter = ev_counter

    # ── RANKINGS ─────────────────────────────────────────────────────────────
    # rank_001 → JOB_0000003 (React/Next.js job, 5 candidates)
    # rank_002 → JOB_0000001 (AI Engineer job, full 6 candidates)

    def _score_candidate(cand_id: str, required: list[str], preferred: list[str]) -> dict:
        cand = candidate_service._candidates_db.get(cand_id, {})
        cand_skills = cand.get("normalized_skills", [])
        missing_required = [s for s in required if s not in cand_skills]
        req_ratio = (len(required) - len(missing_required)) / len(required) if required else 1.0
        pref_missing = [s for s in preferred if s not in cand_skills]
        pref_ratio = (len(preferred) - len(pref_missing)) / len(preferred) if preferred else 1.0
        structured = 0.8 * req_ratio + 0.2 * pref_ratio if preferred else req_ratio
        sem = 0.0
        fit = round(max(0.0, min(1.0, 0.4 * sem + 0.6 * structured * (0.8 if missing_required else 1.0))), 2)
        conf = round(max(0.15, min(0.95, cand.get("confidence_score", 0.5) - 0.15 * len(missing_required) * 0.05)), 2)
        reasons = []
        matched = [s for s in required if s in cand_skills]
        if matched:
            reasons.append(f"Direct evidence of {', '.join(matched[:3])} in profile.")
        if missing_required:
            reasons.append(f"Missing required skills: {', '.join(missing_required)}.")
        if conf < 0.65:
            reasons.append("Profile has low parsing confidence — review manually.")
        return {
            "candidate_id": cand_id,
            "fit_score": fit,
            "confidence_score": conf,
            "missing_required_skills": missing_required,
            "top_match_reasons": reasons,
            "semantic_score": sem,
        }

    # rank_001: JOB_0000003 (react, next.js, python, fastapi) — 5 candidates
    job3_required = ["react", "next.js", "python", "fastapi"]
    job3_preferred = ["docker", "aws"]
    rank001_cand_ids = [f"CAND_{i:07d}" for i in range(1, 6)]
    rank001_scored = [_score_candidate(cid, job3_required, job3_preferred) for cid in rank001_cand_ids]
    rank001_scored.sort(key=lambda x: (-x["fit_score"], -x["confidence_score"], x["candidate_id"]))
    for pos, item in enumerate(rank001_scored, start=1):
        item["rank_position"] = pos

    ranking_service._rankings_db["rank_001"] = {
        "ranking_id": "rank_001",
        "job_id": "JOB_0000003",
        "status": RankingStatus.COMPLETED,
        "candidate_count": len(rank001_scored),
        "created_at": now,
        "updated_at": now,
        "candidates": rank001_scored,
    }

    # rank_002: JOB_0000001 (python, fastapi, faiss, nlp) — all 6 candidates
    job1_required = ["python", "fastapi", "faiss", "nlp"]
    job1_preferred = ["distributed_systems", "spacy"]
    rank002_cand_ids = [f"CAND_{i:07d}" for i in range(1, 7)]
    rank002_scored = [_score_candidate(cid, job1_required, job1_preferred) for cid in rank002_cand_ids]
    rank002_scored.sort(key=lambda x: (-x["fit_score"], -x["confidence_score"], x["candidate_id"]))
    for pos, item in enumerate(rank002_scored, start=1):
        item["rank_position"] = pos

    ranking_service._rankings_db["rank_002"] = {
        "ranking_id": "rank_002",
        "job_id": "JOB_0000001",
        "status": RankingStatus.COMPLETED,
        "candidate_count": len(rank002_scored),
        "created_at": now,
        "updated_at": now,
        "candidates": rank002_scored,
    }

    ranking_service._ranking_counter = 2

    # ── ALERTS ────────────────────────────────────────────────────────────────
    any_low_conf_001 = any(c["confidence_score"] < 0.65 for c in rank001_scored)
    if any_low_conf_001:
        alerts_service._alerts_db["alert_rank_001"] = {
            "alert_id": "alert_rank_001",
            "alert_type": "LOW_CONFIDENCE_RANKING",
            "condition_key": "LOW_CONFIDENCE_RANKING:rank_001",
            "source_entity_id": "rank_001",
            "status": AlertStatus.ACTIVE,
            "severity": AlertSeverity.HIGH,
            "title": "Ranking confidence is low for Full-Stack Engineer – React & Next.js",
            "message": "Some candidates have low confidence scores. Review manually before shortlisting.",
            "created_at": now,
            "job_id": "JOB_0000003",
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
            "notes": "Alert created by system evaluation on startup.",
        }
        alerts_service._alert_counter = 1
        alerts_service._event_counter = 1
