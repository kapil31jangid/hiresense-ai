from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Sequence, Tuple

from app.common.runtime import load_settings


REFERENCE_DATE = date(2026, 6, 19)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

ROLE_SKILL_GROUPS: Dict[str, Tuple[Tuple[str, ...], float]] = {
    "python": (("python", "python3"), 1.0),
    "machine_learning": (("machine learning", "ml", "predictive model", "modeling"), 1.0),
    "deep_learning": (("deep learning", "neural network", "pytorch", "tensorflow"), 0.85),
    "nlp": (("nlp", "natural language processing", "text classification", "language model"), 0.9),
    "llm": (("llm", "large language model", "gpt", "gemini", "openai", "llama", "mistral"), 1.0),
    "fine_tuning": (("fine tuning", "fine-tuning", "finetuning", "lora", "qlora", "peft"), 0.95),
    "embeddings": (("embedding", "embeddings", "sentence transformer", "semantic vector"), 1.0),
    "retrieval": (("retrieval", "semantic search", "vector search", "rag", "hybrid search"), 1.0),
    "ranking": (("ranking", "ranker", "matching", "recommendation", "relevance"), 1.0),
    "vector_database": (("faiss", "milvus", "pinecone", "weaviate", "qdrant", "ann"), 0.8),
    "backend": (("api", "backend", "fastapi", "django", "flask", "microservice"), 0.7),
    "mlops": (("mlops", "model serving", "bentoml", "mlflow", "kubeflow", "airflow"), 0.75),
    "cloud": (("gcp", "google cloud", "aws", "azure", "cloud run", "kubernetes"), 0.55),
    "data_engineering": (("spark", "kafka", "etl", "pipeline", "feature engineering"), 0.6),
}

ALL_ROLE_ALIASES = tuple(alias for aliases, _ in ROLE_SKILL_GROUPS.values() for alias in aliases)
TOTAL_ROLE_WEIGHT = sum(weight for _, weight in ROLE_SKILL_GROUPS.values())
PROFICIENCY_WEIGHT = {
    "beginner": 0.45,
    "intermediate": 0.65,
    "advanced": 0.88,
    "expert": 1.0,
}

PRODUCTION_TERMS = (
    "production",
    "deployed",
    "shipped",
    "scaled",
    "monitoring",
    "observability",
    "latency",
    "api",
    "pipeline",
    "platform",
    "system",
    "users",
    "customers",
    "release",
)

PRODUCT_TERMS = (
    "product",
    "recruiter",
    "workflow",
    "matching",
    "ranking",
    "shortlist",
    "user",
    "customer",
    "startup",
    "founding",
    "0 to 1",
)

LEADERSHIP_TERMS = (
    "mentor",
    "mentored",
    "lead",
    "led",
    "architect",
    "owned",
    "hired",
    "team",
)

INDIA_TIER_ONE_LOCATIONS = (
    "pune",
    "noida",
    "delhi",
    "gurgaon",
    "gurugram",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "mumbai",
    "chennai",
)


@dataclass(frozen=True)
class RankedCandidate:
    candidate_id: str
    score: float
    reasoning: str


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(_clean_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_clean_text(item)}" for key, item in value.items())
    return str(value)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_match_text(value: str) -> str:
    return f" {re.sub(r'[^a-z0-9.+#-]+', ' ', value.lower())} "


@lru_cache(maxsize=512)
def _normalize_alias(value: str) -> str:
    return _normalize_match_text(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y"}
    return bool(value)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@lru_cache(maxsize=1)
def _load_score_calibration() -> Dict[str, float]:
    settings = load_settings()
    path = Path(settings.challenge_calibration_path)
    if not path.is_absolute():
        path = REPOSITORY_ROOT / path
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        calibration = payload.get("score_calibration") or {}
        required = ("minimum", "p25", "median", "p75", "maximum")
        if not all(key in calibration for key in required):
            return {}
        return {key: float(calibration[key]) for key in required}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _calibrate_score(raw_score: float) -> float:
    calibration = _load_score_calibration()
    if not calibration:
        return _clamp(raw_score)

    anchors = [
        (calibration["minimum"], 0.10),
        (calibration["p25"], 0.35),
        (calibration["median"], 0.55),
        (calibration["p75"], 0.75),
        (calibration["maximum"], 0.95),
    ]
    if raw_score <= anchors[0][0]:
        return anchors[0][1]
    if raw_score >= anchors[-1][0]:
        return min(1.0, anchors[-1][1] + (raw_score - anchors[-1][0]) * 0.25)

    for (left_x, left_y), (right_x, right_y) in zip(anchors, anchors[1:]):
        if left_x <= raw_score <= right_x:
            if right_x == left_x:
                return right_y
            ratio = (raw_score - left_x) / (right_x - left_x)
            return _clamp(left_y + ratio * (right_y - left_y))
    return _clamp(raw_score)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _days_since(value: Any) -> int | None:
    parsed = _parse_date(value)
    if parsed is None:
        return None
    return max(0, (REFERENCE_DATE - parsed).days)


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}") from exc
            if isinstance(payload, dict):
                yield payload


def iter_candidate_records(path: str | Path) -> Iterator[Dict[str, Any]]:
    candidate_path = Path(path)
    suffixes = [suffix.lower() for suffix in candidate_path.suffixes]
    if suffixes[-2:] == [".jsonl", ".gz"] or suffixes[-1:] == [".jsonl"]:
        yield from _iter_jsonl(candidate_path)
        return

    with open(candidate_path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(payload, dict):
        candidates = payload.get("candidates") or payload.get("data") or []
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    yield item


def resolve_default_candidates_path(use_sample: bool = False) -> Path:
    settings = load_settings()
    configured_path = settings.challenge_sample_candidates_path if use_sample else settings.challenge_candidates_path
    if configured_path:
        candidate_path = Path(configured_path)
        if not candidate_path.is_absolute():
            candidate_path = REPOSITORY_ROOT / candidate_path
        if candidate_path.exists():
            return candidate_path
    else:
        from app.challenge.downloader import DEFAULT_CACHE_DIR
        candidate_path = DEFAULT_CACHE_DIR / ("sample_candidates.json" if use_sample else "candidates.jsonl")
        if candidate_path.exists():
            return candidate_path

    try:
        from app.challenge.downloader import download_and_decompress
        return download_and_decompress(use_sample=use_sample)
    except Exception as e:
        raise FileNotFoundError(
            f"Dataset file not found locally and GCS download failed.\n"
            f"Please run dataset preparation or configure correct paths.\nDetail: {e}"
        ) from e


def resolve_output_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def _skill_entries(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    skills = candidate.get("skills") or []
    entries: List[Dict[str, Any]] = []
    for skill in skills:
        if isinstance(skill, dict):
            name = str(skill.get("name") or "").strip()
            if name:
                entries.append(skill)
        elif isinstance(skill, str) and skill.strip():
            entries.append({"name": skill.strip()})
    return entries


def _skill_text(candidate: Dict[str, Any]) -> str:
    parts = []
    for skill in _skill_entries(candidate):
        parts.append(
            " ".join(
                [
                    str(skill.get("name") or ""),
                    str(skill.get("proficiency") or ""),
                    str(skill.get("duration_months") or ""),
                ]
            )
        )
    return " ".join(parts)


def _candidate_text(candidate: Dict[str, Any]) -> str:
    profile = candidate.get("profile") or {}
    career_history = candidate.get("career_history") or []
    education = candidate.get("education") or []
    certifications = candidate.get("certifications") or []
    languages = candidate.get("languages") or []
    signals = candidate.get("redrob_signals") or {}

    parts = [
        _clean_text(profile),
        _skill_text(candidate),
        _clean_text(career_history),
        _clean_text(education),
        _clean_text(certifications),
        _clean_text(languages),
        _clean_text(signals),
    ]
    return _normalize_match_text(_normalize_space(" ".join(parts)))


def _count_alias_hits(text: str, aliases: Sequence[str]) -> int:
    hits = 0
    for alias in aliases:
        normalized_alias = _normalize_alias(alias)
        if normalized_alias in text:
            hits += 1
    return hits


def _skill_match_score(candidate: Dict[str, Any], text: str) -> Tuple[float, List[str]]:
    matched: List[str] = []
    weighted_score = 0.0
    skill_blob = _normalize_match_text(_skill_text(candidate))

    skill_quality_by_group: Dict[str, float] = {}
    for entry in _skill_entries(candidate):
        name = _normalize_match_text(str(entry.get("name") or ""))
        proficiency = PROFICIENCY_WEIGHT.get(str(entry.get("proficiency") or "").lower(), 0.7)
        endorsements = min(_safe_float(entry.get("endorsements")), 25.0) / 25.0
        duration = min(_safe_float(entry.get("duration_months")), 48.0) / 48.0
        quality = _clamp(0.55 * proficiency + 0.2 * endorsements + 0.25 * duration)
        for group, (aliases, _) in ROLE_SKILL_GROUPS.items():
            if _count_alias_hits(name, aliases):
                skill_quality_by_group[group] = max(skill_quality_by_group.get(group, 0.0), quality)

    signals = candidate.get("redrob_signals") or {}
    assessment_scores = signals.get("skill_assessment_scores") if isinstance(signals, dict) else {}
    if isinstance(assessment_scores, dict):
        for assessment_name, assessment_score in assessment_scores.items():
            assessment_text = _normalize_match_text(str(assessment_name))
            normalized_assessment = _clamp(_safe_float(assessment_score) / 100.0)
            for group, (aliases, _) in ROLE_SKILL_GROUPS.items():
                if _count_alias_hits(assessment_text, aliases):
                    skill_quality_by_group[group] = max(
                        skill_quality_by_group.get(group, 0.0),
                        normalized_assessment,
                    )

    for group, (aliases, weight) in ROLE_SKILL_GROUPS.items():
        direct_quality = skill_quality_by_group.get(group, 0.0)
        text_quality = min(1.0, _count_alias_hits(f"{skill_blob} {text}", aliases) / 2.0)
        quality = max(direct_quality, text_quality * 0.75)
        if quality > 0:
            matched.append(group)
        weighted_score += weight * quality

    return _clamp(weighted_score / TOTAL_ROLE_WEIGHT), matched


def _keyword_density_score(text: str, terms: Sequence[str]) -> float:
    if not text:
        return 0.0
    hits = _count_alias_hits(text, terms)
    return _clamp(hits / max(1.0, min(8.0, len(terms) * 0.45)))


def _experience_score(candidate: Dict[str, Any]) -> float:
    profile = candidate.get("profile") or {}
    years = _safe_float(profile.get("years_of_experience"))
    if years <= 0:
        months = 0.0
        for role in candidate.get("career_history") or []:
            if isinstance(role, dict):
                months += _safe_float(role.get("duration_months"))
        years = months / 12.0

    if 5.0 <= years <= 9.0:
        return 1.0
    if 3.0 <= years < 5.0:
        return 0.65 + (years - 3.0) * 0.15
    if 9.0 < years <= 12.0:
        return 0.95 - (years - 9.0) * 0.08
    if years > 12.0:
        return 0.65
    return _clamp(years / 5.0)


def _title_score(candidate: Dict[str, Any], text: str) -> float:
    profile = candidate.get("profile") or {}
    title_text = " ".join(
        [
            str(profile.get("current_title") or ""),
            str(profile.get("headline") or ""),
            " ".join(str(item.get("title") or "") for item in candidate.get("career_history") or [] if isinstance(item, dict)),
        ]
    ).lower()
    strong_titles = (
        "ai engineer",
        "machine learning engineer",
        "ml engineer",
        "senior ai",
        "senior machine learning",
        "applied scientist",
        "ranking engineer",
        "search engineer",
    )
    adjacent_titles = ("data scientist", "backend engineer", "software engineer", "data engineer")
    if _count_alias_hits(title_text, strong_titles):
        return 1.0
    if _count_alias_hits(title_text, adjacent_titles):
        return 0.68
    return 0.35 if _count_alias_hits(text, ("model", "machine learning", "python")) else 0.1


def _behavior_score(candidate: Dict[str, Any]) -> Tuple[float, List[str]]:
    signals = candidate.get("redrob_signals") or {}
    if not isinstance(signals, dict):
        return 0.35, ["behavioral signals unavailable"]

    score_parts: List[float] = []
    notes: List[str] = []

    completeness = _clamp(_safe_float(signals.get("profile_completeness_score")) / 100.0)
    score_parts.append(completeness)
    if completeness < 0.55:
        notes.append("low profile completeness")

    days_inactive = _days_since(signals.get("last_active_date"))
    if days_inactive is None:
        recency = 0.35
        notes.append("missing recent activity")
    elif days_inactive <= 7:
        recency = 1.0
    elif days_inactive <= 30:
        recency = 0.82
    elif days_inactive <= 90:
        recency = 0.55
    else:
        recency = 0.25
        notes.append("stale activity")
    score_parts.append(recency)

    open_to_work = _safe_bool(signals.get("open_to_work_flag"))
    score_parts.append(1.0 if open_to_work else 0.45)
    if open_to_work:
        notes.append("open to work")

    response_rate = _clamp(_safe_float(signals.get("recruiter_response_rate")))
    score_parts.append(response_rate if response_rate else 0.35)
    if response_rate < 0.35:
        notes.append("low recruiter response rate")

    response_hours = _safe_float(signals.get("avg_response_time_hours"), default=72.0)
    response_speed = 1.0 if response_hours <= 12 else 0.75 if response_hours <= 36 else 0.45 if response_hours <= 72 else 0.2
    score_parts.append(response_speed)

    notice_days = _safe_float(signals.get("notice_period_days"), default=90.0)
    notice_score = 1.0 if notice_days <= 30 else 0.75 if notice_days <= 60 else 0.45 if notice_days <= 90 else 0.2
    score_parts.append(notice_score)
    if notice_days <= 30:
        notes.append("short notice period")

    market_interest = (
        min(_safe_float(signals.get("saved_by_recruiters_30d")), 10.0) / 10.0
        + min(_safe_float(signals.get("search_appearance_30d")), 100.0) / 100.0
        + min(_safe_float(signals.get("profile_views_received_30d")), 100.0) / 100.0
    ) / 3.0
    score_parts.append(market_interest)

    github_score = _clamp(_safe_float(signals.get("github_activity_score")) / 100.0)
    score_parts.append(github_score)

    interview_score = _clamp(_safe_float(signals.get("interview_completion_rate"), default=0.5))
    offer_score = _clamp(_safe_float(signals.get("offer_acceptance_rate"), default=0.5))
    score_parts.extend([interview_score, offer_score])

    verification_score = sum(
        1.0
        for key in ("verified_email", "verified_phone", "linkedin_connected")
        if _safe_bool(signals.get(key))
    ) / 3.0
    score_parts.append(verification_score)

    return _clamp(sum(score_parts) / len(score_parts)), notes[:3]


def _location_score(candidate: Dict[str, Any]) -> float:
    profile = candidate.get("profile") or {}
    signals = candidate.get("redrob_signals") or {}
    location_text = f"{profile.get('location', '')} {profile.get('country', '')}".lower()
    preferred_work_mode = ""
    willing_to_relocate = False
    if isinstance(signals, dict):
        preferred_work_mode = str(signals.get("preferred_work_mode") or "").lower()
        willing_to_relocate = _safe_bool(signals.get("willing_to_relocate"))

    score = 0.35
    if "india" in location_text or any(city in location_text for city in INDIA_TIER_ONE_LOCATIONS):
        score += 0.25
    if "pune" in location_text or "noida" in location_text:
        score += 0.2
    elif willing_to_relocate:
        score += 0.18
    if "hybrid" in preferred_work_mode or "onsite" in preferred_work_mode:
        score += 0.12
    elif "remote" in preferred_work_mode and willing_to_relocate:
        score += 0.05
    return _clamp(score)


def _research_only_penalty(text: str, production_score: float) -> float:
    research_hits = _count_alias_hits(text, ("research", "paper", "publication", "phd", "academic"))
    if research_hits >= 2 and production_score < 0.35:
        return 0.12
    return 0.0


def _salary_penalty(candidate: Dict[str, Any]) -> float:
    signals = candidate.get("redrob_signals") or {}
    if not isinstance(signals, dict):
        return 0.0
    salary = signals.get("expected_salary_range_inr_lpa")
    if isinstance(salary, dict):
        high = _safe_float(salary.get("max") or salary.get("upper") or salary.get("to"))
        low = _safe_float(salary.get("min") or salary.get("lower") or salary.get("from"))
        midpoint = (low + high) / 2.0 if high and low else high or low
    elif isinstance(salary, (list, tuple)) and salary:
        values = [_safe_float(item) for item in salary]
        midpoint = sum(values) / len(values)
    else:
        midpoint = _safe_float(salary)
    if midpoint >= 80:
        return 0.08
    if midpoint >= 60:
        return 0.04
    return 0.0


def _profile_consistency_penalty(candidate: Dict[str, Any]) -> Tuple[float, List[str]]:
    profile = candidate.get("profile") or {}
    total_months = max(0.0, _safe_float(profile.get("years_of_experience")) * 12.0)
    penalty = 0.0
    concerns: List[str] = []

    impossible_skills = 0
    unsupported_expert_skills = 0
    for skill in _skill_entries(candidate):
        duration = _safe_float(skill.get("duration_months"))
        proficiency = str(skill.get("proficiency") or "").lower()
        if total_months > 0 and duration > total_months + 12:
            impossible_skills += 1
        if proficiency == "expert" and duration <= 0:
            unsupported_expert_skills += 1

    if impossible_skills:
        penalty += min(0.18, 0.06 * impossible_skills)
        concerns.append("skill duration exceeds stated experience")
    if unsupported_expert_skills >= 3:
        penalty += min(0.18, 0.03 * unsupported_expert_skills)
        concerns.append("multiple expert claims lack usage history")

    inconsistent_roles = 0
    current_roles = 0
    for role in candidate.get("career_history") or []:
        if not isinstance(role, dict):
            continue
        current_roles += int(_safe_bool(role.get("is_current")))
        duration = _safe_float(role.get("duration_months"))
        start = _parse_date(role.get("start_date"))
        end = _parse_date(role.get("end_date")) or (REFERENCE_DATE if _safe_bool(role.get("is_current")) else None)
        if start and end:
            elapsed_months = max(0.0, (end - start).days / 30.4375)
            if end < start or duration > elapsed_months + 3:
                inconsistent_roles += 1
        if total_months > 0 and duration > total_months + 12:
            inconsistent_roles += 1

    if inconsistent_roles:
        penalty += min(0.2, 0.08 * inconsistent_roles)
        concerns.append("career dates conflict with claimed duration")
    if current_roles > 2:
        penalty += 0.05
        concerns.append("unusually many concurrent current roles")
    return min(0.4, penalty), concerns


def score_candidate(candidate: Dict[str, Any], apply_calibration: bool = False) -> RankedCandidate:
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    if not candidate_id:
        raise ValueError("Candidate record is missing candidate_id.")

    text = _candidate_text(candidate)
    skill_score, matched_groups = _skill_match_score(candidate, text)
    semantic_role_score = _keyword_density_score(text, ALL_ROLE_ALIASES)
    production_score = _keyword_density_score(text, PRODUCTION_TERMS)
    product_score = _keyword_density_score(text, PRODUCT_TERMS)
    leadership_score = _keyword_density_score(text, LEADERSHIP_TERMS)
    experience_score = _experience_score(candidate)
    title_score = _title_score(candidate, text)
    behavior_score, behavior_notes = _behavior_score(candidate)
    location_score = _location_score(candidate)
    consistency_penalty, consistency_notes = _profile_consistency_penalty(candidate)

    raw_score = (
        0.32 * skill_score
        + 0.16 * semantic_role_score
        + 0.13 * production_score
        + 0.08 * product_score
        + 0.05 * leadership_score
        + 0.10 * experience_score
        + 0.06 * title_score
        + 0.07 * behavior_score
        + 0.03 * location_score
    )
    raw_score -= _research_only_penalty(text, production_score)
    raw_score -= _salary_penalty(candidate)
    raw_score -= consistency_penalty

    score = round(_calibrate_score(raw_score) if apply_calibration else _clamp(raw_score), 6)
    reasoning = _build_reasoning(candidate, matched_groups, behavior_notes + consistency_notes, score)
    return RankedCandidate(candidate_id=candidate_id, score=score, reasoning=reasoning)


def _build_reasoning(
    candidate: Dict[str, Any],
    matched_groups: Sequence[str],
    behavior_notes: Sequence[str],
    score: float,
) -> str:
    profile = candidate.get("profile") or {}
    title = str(profile.get("current_title") or profile.get("headline") or "Candidate").strip()
    years = _safe_float(profile.get("years_of_experience"))
    matched = ", ".join(group.replace("_", " ") for group in matched_groups[:5]) or "limited direct AI evidence"
    notes = ", ".join(behavior_notes[:2]) or "behavioral signals reviewed"
    confidence_hint = "strong" if score >= 0.72 else "moderate" if score >= 0.5 else "limited"
    reasoning = (
        f"{title} with {years:.1f} years shows {confidence_hint} fit through evidence in {matched}; "
        f"{notes}."
    )
    return _normalize_space(reasoning)[:500]


def rank_candidates(records: Iterable[Dict[str, Any]], top_k: int = 100) -> List[RankedCandidate]:
    scored: List[RankedCandidate] = []
    for record in records:
        scored.append(score_candidate(record))
    scored.sort(key=lambda item: (-item.score, item.candidate_id))
    return scored[:top_k]


def write_submission(rows: Sequence[RankedCandidate], output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        previous_score = math.inf
        for rank, row in enumerate(rows, start=1):
            if row.score > previous_score:
                raise ValueError("Ranked rows must be sorted by non-increasing score.")
            previous_score = row.score
            writer.writerow(
                {
                    "candidate_id": row.candidate_id,
                    "rank": rank,
                    "score": f"{row.score:.6f}",
                    "reasoning": row.reasoning,
                }
            )


def run_submission(candidates_path: str | Path, output_path: str | Path, top_k: int = 100, strict: bool = False) -> List[RankedCandidate]:
    rows = rank_candidates(iter_candidate_records(candidates_path), top_k=top_k)
    if strict and len(rows) != top_k:
        raise ValueError(f"Strict mode expected {top_k} ranked rows, but generated {len(rows)}.")
    write_submission(rows, output_path)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an offline HireSense AI challenge submission CSV.",
    )
    parser.add_argument("--candidates", help="Path to candidates.jsonl, candidates.jsonl.gz, or sample_candidates.json. Defaults to CHALLENGE_CANDIDATES_PATH.")
    parser.add_argument("--sample", action="store_true", help="Use CHALLENGE_SAMPLE_CANDIDATES_PATH or sample_candidates.json from CHALLENGE_DATASET_DIR.")
    parser.add_argument("--output", help="Path to write the submission CSV. Defaults to CHALLENGE_SUBMISSION_OUTPUT_PATH.")
    parser.add_argument("--top-k", type=int, default=100, help="Number of ranked candidates to export. Defaults to 100.")
    parser.add_argument("--strict", action="store_true", help="Require exactly top-k rows in the generated output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        candidates_path = Path(args.candidates) if args.candidates else resolve_default_candidates_path(use_sample=args.sample)
        output_path = resolve_output_path(args.output or settings.challenge_submission_output_path)
        rows = run_submission(candidates_path, output_path, top_k=args.top_k, strict=args.strict)
    except Exception as exc:
        print(f"submission_generation_failed: {exc}", file=sys.stderr)
        return 1
    print(f"submission_generated: rows={len(rows)} output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
