from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from jsonschema import Draft7Validator, FormatChecker

from app.challenge.offline_ranker import (
    iter_candidate_records,
    resolve_default_candidates_path,
    score_candidate,
)
from app.common.runtime import load_settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SUBMISSION_COLUMNS = ["candidate_id", "rank", "score", "reasoning"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _resolve_artifact_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def _load_schema_validator(schema_path: Path) -> Draft7Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=FormatChecker())


def _validate_record(validator: Draft7Validator, record: Dict[str, Any], source: str) -> None:
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if not errors:
        return
    error = errors[0]
    field = ".".join(str(part) for part in error.absolute_path) or "<root>"
    raise ValueError(f"Schema validation failed for {source} at {field}: {error.message}")


def _validate_submission_reference(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
    if header != SUBMISSION_COLUMNS:
        raise ValueError(
            f"Organizer submission header mismatch in {path}: expected {SUBMISSION_COLUMNS}, found {header}."
        )


def _resolve_bundle_file(configured: str, dataset_dir: str, filename: str) -> Path:
    if configured:
        path = Path(configured)
    elif dataset_dir:
        path = Path(dataset_dir) / filename
    else:
        raise FileNotFoundError(f"No path configured for organizer file: {filename}")
    if not path.exists():
        raise FileNotFoundError(f"Organizer file does not exist: {path}")
    return path


def inspect_sample(
    sample_path: Path,
    output_path: Path,
    validator: Draft7Validator,
    schema_path: Path,
) -> Dict[str, Any]:
    records = list(iter_candidate_records(sample_path))
    if not records:
        raise ValueError(f"No candidate records found in sample file: {sample_path}")

    candidate_ids: set[str] = set()
    duplicate_ids: List[str] = []
    scores: List[float] = []
    profile_complete = 0
    skills_present = 0
    career_present = 0
    signals_present = 0

    for record in records:
        candidate_id = str(record.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("Sample candidate is missing candidate_id.")
        if candidate_id in candidate_ids:
            duplicate_ids.append(candidate_id)
        candidate_ids.add(candidate_id)
        _validate_record(validator, record, f"sample candidate {candidate_id}")

        profile = record.get("profile") or {}
        signals = record.get("redrob_signals") or {}
        profile_complete += int(bool(profile))
        skills_present += int(bool(record.get("skills")))
        career_present += int(bool(record.get("career_history")))
        signals_present += int(bool(signals))
        scores.append(score_candidate(record, apply_calibration=False).score)

    report = {
        "artifact_type": "SAMPLE_CALIBRATION",
        "generated_at": _utc_now(),
        "sample_path": str(sample_path.resolve()),
        "schema_path": str(schema_path.resolve()),
        "schema_validated_count": len(records),
        "sample_count": len(records),
        "unique_candidate_count": len(candidate_ids),
        "duplicate_candidate_ids": sorted(set(duplicate_ids)),
        "feature_coverage": {
            "profile": round(profile_complete / len(records), 4),
            "skills": round(skills_present / len(records), 4),
            "career_history": round(career_present / len(records), 4),
            "redrob_signals": round(signals_present / len(records), 4),
        },
        "score_calibration": {
            "minimum": min(scores),
            "p25": round(_percentile(scores, 0.25), 6),
            "median": round(statistics.median(scores), 6),
            "p75": round(_percentile(scores, 0.75), 6),
            "maximum": max(scores),
            "mean": round(statistics.fmean(scores), 6),
            "population_stddev": round(statistics.pstdev(scores), 6),
        },
        "training_mode": "UNLABELED_SCHEMA_INSPECTION",
        "training_note": (
            "The organizer sample has no relevance labels. It is used only to validate schema, "
            "feature extraction, and score distribution; it does not alter final ranking scores."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _summary_from_record(record: Dict[str, Any], offset: int) -> Dict[str, Any]:
    profile = record.get("profile") or {}
    signals = record.get("redrob_signals") if isinstance(record.get("redrob_signals"), dict) else {}
    completeness = _safe_float(signals.get("profile_completeness_score")) / 100.0
    updated_at = str(signals.get("last_active_date") or "2026-06-20").strip()
    if len(updated_at) == 10:
        updated_at = f"{updated_at}T00:00:00Z"
    return {
        "candidate_id": str(record.get("candidate_id") or ""),
        "full_name": profile.get("anonymized_name") or record.get("candidate_id"),
        "confidence_score": round(max(0.1, min(0.99, completeness)), 2),
        "parsing_status": "COMPLETED",
        "updated_at": updated_at.replace("+00:00", "Z"),
        "source": "CHALLENGE_DATASET",
        "_offset": offset,
    }


def build_full_index(
    candidates_path: Path,
    output_path: Path,
    validator: Draft7Validator,
    schema_path: Path,
) -> Dict[str, Any]:
    if candidates_path.suffix.lower() == ".gz":
        raise ValueError("Webapp byte-offset indexing requires an uncompressed candidates.jsonl file.")

    summaries: List[Dict[str, Any]] = []
    candidate_ids: set[str] = set()
    duplicate_ids: List[str] = []
    malformed_count = 0

    with candidates_path.open("rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                continue
            candidate_id = str(record.get("candidate_id") or "").strip()
            if not candidate_id:
                malformed_count += 1
                continue
            if candidate_id in candidate_ids:
                duplicate_ids.append(candidate_id)
                continue
            _validate_record(validator, record, f"candidate {candidate_id} at byte offset {offset}")
            candidate_ids.add(candidate_id)
            summaries.append(_summary_from_record(record, offset))

    summaries.sort(key=lambda item: item["candidate_id"])
    stat = candidates_path.stat()
    artifact = {
        "artifact_type": "CHALLENGE_DATASET_INDEX",
        "generated_at": _utc_now(),
        "source_path": str(candidates_path.resolve()),
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "schema_path": str(schema_path.resolve()),
        "schema_validated_count": len(summaries),
        "candidate_count": len(summaries),
        "malformed_record_count": malformed_count,
        "duplicate_candidate_ids": sorted(set(duplicate_ids)),
        "summaries": summaries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    return artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the organizer bundle and index the full candidate dataset.",
    )
    parser.add_argument("--sample", help="Path to sample_candidates.json.")
    parser.add_argument("--candidates", help="Path to the full candidates.jsonl.")
    parser.add_argument("--schema", help="Path to candidate_schema.json.")
    parser.add_argument("--sample-submission", help="Path to sample_submission.csv.")
    parser.add_argument("--calibration-output", help="Path for the sample calibration artifact.")
    parser.add_argument("--index-output", help="Path for the full dataset index artifact.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    try:
        sample_path = Path(args.sample) if args.sample else resolve_default_candidates_path(use_sample=True)
        candidates_path = Path(args.candidates) if args.candidates else resolve_default_candidates_path(use_sample=False)
        schema_path = Path(args.schema) if args.schema else _resolve_bundle_file(
            settings.challenge_schema_path,
            settings.challenge_dataset_dir,
            "candidate_schema.json",
        )
        sample_submission_path = Path(args.sample_submission) if args.sample_submission else _resolve_bundle_file(
            settings.challenge_sample_submission_path,
            settings.challenge_dataset_dir,
            "sample_submission.csv",
        )
        calibration_path = _resolve_artifact_path(args.calibration_output or settings.challenge_calibration_path)
        index_path = _resolve_artifact_path(args.index_output or settings.challenge_index_path)

        validator = _load_schema_validator(schema_path)
        _validate_submission_reference(sample_submission_path)
        calibration = inspect_sample(sample_path, calibration_path, validator, schema_path)
        index = build_full_index(candidates_path, index_path, validator, schema_path)
        sample_ids = [record["candidate_id"] for record in iter_candidate_records(sample_path)]
        indexed_prefix = [summary["candidate_id"] for summary in index["summaries"][: len(sample_ids)]]
        if sample_ids != indexed_prefix:
            raise ValueError("sample_candidates.json does not match the documented prefix of candidates.jsonl.")
    except Exception as exc:
        print(f"dataset_preparation_failed: {exc}", file=sys.stderr)
        return 1

    print(
        "dataset_prepared: "
        f"sample_count={calibration['sample_count']} "
        f"full_candidate_count={index['candidate_count']} "
        f"schema_validated={index['schema_validated_count']} "
        f"calibration={calibration_path} index={index_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
