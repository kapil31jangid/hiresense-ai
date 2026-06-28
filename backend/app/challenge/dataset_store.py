from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.common.runtime import load_settings


_index_loaded = False
_dataset_path: Optional[Path] = None
_candidate_offsets: Dict[str, int] = {}
_candidate_summaries: List[Dict[str, Any]] = []
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "2026-06-20T00:00:00Z"
    if len(text) == 10:
        return f"{text}T00:00:00Z"
    return text.replace("+00:00", "Z")


def _skill_names(record: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for skill in record.get("skills") or []:
        if isinstance(skill, dict):
            name = str(skill.get("name") or "").strip()
        else:
            name = str(skill or "").strip()
        if name and name.lower() not in {item.lower() for item in names}:
            names.append(name)
    return names


def _behavioral_signal_labels(signals: Dict[str, Any]) -> List[str]:
    labels: List[str] = []
    if signals.get("open_to_work_flag"):
        labels.append("open_to_work")
    if _safe_float(signals.get("recruiter_response_rate")) < 0.35:
        labels.append("low_recruiter_response")
    if _safe_float(signals.get("notice_period_days"), 90.0) <= 30:
        labels.append("short_notice_period")
    if signals.get("verified_email"):
        labels.append("verified_email")
    if signals.get("verified_phone"):
        labels.append("verified_phone")
    if signals.get("linkedin_connected"):
        labels.append("linkedin_connected")
    return labels


def _summary_from_record(record: Dict[str, Any], offset: int) -> Dict[str, Any]:
    profile = record.get("profile") or {}
    signals = record.get("redrob_signals") if isinstance(record.get("redrob_signals"), dict) else {}
    return {
        "candidate_id": record.get("candidate_id"),
        "full_name": profile.get("anonymized_name") or record.get("candidate_id"),
        "confidence_score": round(max(0.1, min(0.99, _safe_float(signals.get("profile_completeness_score")) / 100.0)), 2),
        "parsing_status": "COMPLETED",
        "updated_at": _normalize_timestamp(signals.get("last_active_date")),
        "source": "CHALLENGE_DATASET",
        "_offset": offset,
    }


def _record_to_candidate(record: Dict[str, Any]) -> Dict[str, Any]:
    profile = dict(record.get("profile") or {})
    signals = record.get("redrob_signals") if isinstance(record.get("redrob_signals"), dict) else {}
    skills = _skill_names(record)
    candidate_id = str(record.get("candidate_id") or "")
    full_name = profile.get("anonymized_name") or candidate_id
    updated_at = _normalize_timestamp(signals.get("last_active_date"))
    confidence_score = round(max(0.1, min(0.99, _safe_float(signals.get("profile_completeness_score")) / 100.0)), 2)

    profile["full_name"] = full_name
    profile.setdefault("email", None)

    return {
        "candidate_id": candidate_id,
        "full_name": full_name,
        "normalized_skills": [skill.lower() for skill in skills],
        "years_of_experience": _safe_float(profile.get("years_of_experience")),
        "confidence_score": confidence_score,
        "parsing_status": "COMPLETED",
        "created_at": _normalize_timestamp(signals.get("signup_date")),
        "updated_at": updated_at,
        "source_type": "CHALLENGE_DATASET",
        "source_file_name": None,
        "source_text": " ".join(
            [
                str(profile.get("headline") or ""),
                str(profile.get("summary") or ""),
                " ".join(str(item.get("description") or "") for item in record.get("career_history") or [] if isinstance(item, dict)),
                " ".join(skills),
            ]
        ).strip(),
        "source_data": record,
        "profile": profile,
        "career_history": record.get("career_history") or [],
        "education": record.get("education") or [],
        "skills": skills,
        "redrob_signals": _behavioral_signal_labels(signals),
        "behavioral_signals": _behavioral_signal_labels(signals),
        "embedding_metadata": {
            "entity_type": "CANDIDATE",
            "entity_id": candidate_id,
            "embedding_version": "challenge_dataset_v1",
            "status": "STALE",
            "source": "CHALLENGE_DATASET",
        },
    }


def is_enabled() -> bool:
    settings = load_settings()
    return str(settings.challenge_dataset_autoload).lower() == "true"


def _resolve_candidates_path() -> Optional[Path]:
    try:
        from app.challenge.offline_ranker import resolve_default_candidates_path
        return resolve_default_candidates_path(use_sample=False)
    except Exception:
        return None


def _load_prebuilt_index(path: Path) -> bool:
    settings = load_settings()
    index_path = Path(settings.challenge_index_path)
    if not index_path.is_absolute():
        index_path = REPOSITORY_ROOT / index_path
    if not index_path.exists():
        return False
    try:
        artifact = json.loads(index_path.read_text(encoding="utf-8"))
        stat = path.stat()
        if artifact.get("artifact_type") != "CHALLENGE_DATASET_INDEX":
            return False
        if str(Path(artifact.get("source_path", "")).resolve()) != str(path.resolve()):
            return False
        if artifact.get("source_size") != stat.st_size or artifact.get("source_mtime_ns") != stat.st_mtime_ns:
            return False
        summaries = artifact.get("summaries")
        if not isinstance(summaries, list):
            return False
        for summary in summaries:
            candidate_id = summary.get("candidate_id")
            offset = summary.get("_offset")
            if candidate_id and isinstance(offset, int):
                _candidate_offsets[candidate_id] = offset
                _candidate_summaries.append(summary)
        return bool(_candidate_summaries)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def ensure_index_loaded() -> None:
    global _index_loaded, _dataset_path
    if _index_loaded or not is_enabled():
        return

    path = _resolve_candidates_path()
    if path is None:
        _index_loaded = True
        return

    _dataset_path = path
    if _load_prebuilt_index(path):
        _index_loaded = True
        return

    import gzip
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            candidate_id = record.get("candidate_id")
            if not candidate_id:
                continue
            _candidate_offsets[candidate_id] = offset
            _candidate_summaries.append(_summary_from_record(record, offset))

    _candidate_summaries.sort(key=lambda item: item["candidate_id"])
    _index_loaded = True


def list_summaries() -> List[Dict[str, Any]]:
    ensure_index_loaded()
    return list(_candidate_summaries)


def has_candidate(candidate_id: str) -> bool:
    ensure_index_loaded()
    return candidate_id in _candidate_offsets


def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    ensure_index_loaded()
    import gzip
    opener = gzip.open if _dataset_path.suffix.lower() == ".gz" else open
    with opener(_dataset_path, "rb") as handle:
        handle.seek(_candidate_offsets[candidate_id])
        line = handle.readline()
    if not line:
        return None
    return _record_to_candidate(json.loads(line))


def index_status() -> Dict[str, Any]:
    ensure_index_loaded()
    return {
        "enabled": is_enabled(),
        "dataset_path": str(_dataset_path) if _dataset_path else None,
        "candidate_count": len(_candidate_summaries),
        "loaded": _index_loaded,
    }
