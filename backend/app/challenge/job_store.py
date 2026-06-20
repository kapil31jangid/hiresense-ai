from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from app.common.runtime import load_settings


CHALLENGE_JOB_ID = "JOB_CHALLENGE_001"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_text = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    xml_text = re.sub(r"</w:p>", "\n", xml_text)
    text = re.sub(r"<[^>]+>", " ", xml_text)
    return _normalize_text(text)


def _resolve_job_description_path() -> Optional[Path]:
    settings = load_settings()
    if not settings.challenge_dataset_dir:
        return None
    path = Path(settings.challenge_dataset_dir) / "job_description.docx"
    return path if path.exists() else None


def get_challenge_job() -> Optional[Dict[str, Any]]:
    settings = load_settings()
    if str(settings.challenge_dataset_autoload).lower() != "true":
        return None

    path = _resolve_job_description_path()
    description = _read_docx_text(path) if path else (
        "Senior AI Engineer role focused on production ranking, semantic search, embeddings, "
        "LLM systems, retrieval, model evaluation, and recruiter workflow intelligence."
    )

    required_skills = [
        "python",
        "machine_learning",
        "nlp",
        "embeddings",
        "retrieval",
        "ranking",
        "llm",
    ]
    preferred_skills = [
        "fine_tuning",
        "vector_database",
        "mlops",
        "backend",
        "cloud",
        "data_engineering",
    ]

    return {
        "job_id": CHALLENGE_JOB_ID,
        "title": "Senior AI Engineer - Intelligent Candidate Discovery",
        "description_text": description,
        "status": "ACTIVE",
        "location": "Pune / Noida / Hybrid",
        "employment_type": "FULL_TIME",
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "confidence_score": 0.95,
        "created_at": "2026-06-20T00:00:00Z",
        "updated_at": "2026-06-20T00:00:00Z",
        "candidate_count": 100000,
        "role_intelligence": {
            "source": "CHALLENGE_DATASET",
            "responsibilities": [
                "Build production ranking and retrieval systems.",
                "Integrate profile, career, and behavioral signals.",
                "Generate recruiter-trustworthy shortlists.",
            ],
            "qualifications": [
                "Strong production ML systems experience.",
                "Semantic search, embeddings, ranking, and LLM familiarity.",
                "Product engineering mindset for recruiter workflows.",
            ],
        },
        "embedding_metadata": {
            "entity_type": "JOB",
            "entity_id": CHALLENGE_JOB_ID,
            "embedding_version": "challenge_job_v1",
            "status": "STALE",
            "source": "CHALLENGE_DATASET",
        },
        "requirement_version": 1,
    }
