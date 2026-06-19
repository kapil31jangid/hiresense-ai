from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import re

from app.common.schemas import JobCreate, JobUpdate, JobResponseData, JobListItem, JobStatus, SourceType
from app.common.errors import HireSenseException
from app.common.repositories import FirestoreBackedStore

_jobs_db: Dict[str, Dict] = FirestoreBackedStore("jobs", {})
_job_requirements_db: Dict[str, List[Dict[str, Any]]] = FirestoreBackedStore("job_requirements", {})
_job_counter = 0

_SKILL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "python": ("python", "python3", "python 3"),
    "fastapi": ("fastapi", "fast api"),
    "postgresql": ("postgresql", "postgres", "postgreSQL", "psql"),
    "spacy": ("spacy", "spaCy"),
    "faiss": ("faiss", "facebook ai similarity search"),
    "react": ("react", "react.js", "reactjs"),
    "next.js": ("next.js", "nextjs", "next js"),
    "docker": ("docker", "containerization", "containers"),
    "aws": ("aws", "amazon web services"),
    "distributed_systems": ("distributed systems", "distributed system", "distributed architecture"),
    "machine_learning": ("machine learning", "ml"),
    "nlp": ("nlp", "natural language processing"),
}

_REQUIRED_CUES = (
    "required",
    "must have",
    "must-have",
    "need",
    "needs",
    "required skills",
    "requirements",
    "qualification",
    "qualifications",
    "strong",
    "proficient",
    "expertise",
    "experience with",
    "experience in",
    "looking for",
)
_PREFERRED_CUES = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "good to have",
    "bonus",
    "plus",
    "advantage",
)
_RESPONSIBILITY_CUES = ("responsibilities", "responsible for", "build", "develop", "maintain", "own", "design")
_QUALIFICATION_CUES = ("qualification", "degree", "years", "experience", "background")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _iter_evidence_units(description_text: str) -> List[Tuple[str, int, int]]:
    units: List[Tuple[str, int, int]] = []
    pattern = re.compile(r".+?(?:(?<=[.;])\s+|\n|$)", re.DOTALL)
    for match in pattern.finditer(description_text):
        source_text = _normalize_text(match.group(0).strip(" \n\t.;:"))
        if source_text:
            units.append((source_text, match.start(), match.end()))
    return units


def _contains_cue(text: str, cues: Tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def _classify_skill_requirement(text: str) -> Optional[str]:
    if _contains_cue(text, _PREFERRED_CUES):
        return "PREFERRED_SKILL"
    if _contains_cue(text, _REQUIRED_CUES):
        return "REQUIRED_SKILL"
    return None


def _find_skills(source_text: str) -> List[str]:
    found: List[str] = []
    lowered = source_text.lower()
    for canonical_skill, aliases in _SKILL_ALIASES.items():
        for alias in aliases:
            pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
            if re.search(pattern, lowered):
                found.append(canonical_skill)
                break
    return found


def _append_unique(values: List[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _build_embedding_metadata(job_id: str, title: str, required_skills: List[str], preferred_skills: List[str]) -> Dict[str, Any]:
    structured_text = " ".join([title, " ".join(required_skills), " ".join(preferred_skills)]).strip()
    return {
        "entity_type": "JOB",
        "entity_id": job_id,
        "embedding_version": "job_requirements_v1",
        "status": "STALE",
        "source_text": structured_text,
    }


def _parse_job_description(data: JobCreate) -> Dict[str, Any]:
    description_text = _normalize_text(data.description_text)
    if len(description_text) < 20:
        raise HireSenseException(
            status_code=400,
            code="INVALID_REQUEST",
            message="description_text must contain enough detail to parse job requirements.",
            details={"field": "description_text"},
        )

    required_skills: List[str] = []
    preferred_skills: List[str] = []
    evidence: List[Dict[str, Any]] = []
    responsibilities: List[str] = []
    qualifications: List[str] = []

    for source_text, span_start, span_end in _iter_evidence_units(data.description_text):
        lowered = source_text.lower()
        requirement_type = _classify_skill_requirement(source_text)
        skills = _find_skills(source_text)

        if requirement_type:
            for skill in skills:
                if requirement_type == "REQUIRED_SKILL":
                    _append_unique(required_skills, skill)
                else:
                    _append_unique(preferred_skills, skill)
                evidence.append({
                    "requirement_type": requirement_type,
                    "canonical_value": skill,
                    "source_text": source_text,
                    "source_span_start": span_start,
                    "source_span_end": span_end,
                    "confidence_score": 0.95 if requirement_type == "REQUIRED_SKILL" else 0.88,
                })

        if _contains_cue(lowered, _RESPONSIBILITY_CUES):
            responsibilities.append(source_text)
            evidence.append({
                "requirement_type": "RESPONSIBILITY",
                "canonical_value": source_text,
                "source_text": source_text,
                "source_span_start": span_start,
                "source_span_end": span_end,
                "confidence_score": 0.80,
            })
        if _contains_cue(lowered, _QUALIFICATION_CUES):
            qualifications.append(source_text)
            evidence.append({
                "requirement_type": "EXPERIENCE",
                "canonical_value": source_text,
                "source_text": source_text,
                "source_span_start": span_start,
                "source_span_end": span_end,
                "confidence_score": 0.78,
            })

    # Keep explicit preferred evidence from general prose when the cue is nearby.
    for skill in list(required_skills):
        if skill in preferred_skills:
            preferred_skills.remove(skill)

    confidence_score = 0.55
    if evidence:
        confidence_score += 0.20
    if required_skills:
        confidence_score += 0.15
    if responsibilities or qualifications:
        confidence_score += 0.05

    return {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "requirement_evidence": evidence,
        "role_intelligence": {
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "requirement_count": len(evidence),
        },
        "confidence_score": round(min(confidence_score, 0.95), 2),
    }


def _store_job_record(job_id: str, job_record: Dict[str, Any], requirement_evidence: List[Dict[str, Any]]) -> None:
    _jobs_db[job_id] = job_record
    _job_requirements_db[job_id] = requirement_evidence

class JobService:
    @staticmethod
    def create_job(data: JobCreate) -> JobResponseData:
        global _job_counter
        # Basic validation
        if not _normalize_text(data.title) or not _normalize_text(data.description_text):
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="Title and description_text are required."
            )

        _job_counter += 1
        job_id = f"JOB_{_job_counter:07d}"
        parsed = _parse_job_description(data)
        now_str = _utc_now()

        job_record = {
            "job_id": job_id,
            "title": _normalize_text(data.title),
            "description_text": _normalize_text(data.description_text),
            "status": JobStatus.ACTIVE,
            "location": data.location,
            "employment_type": data.employment_type,
            "required_skills": parsed["required_skills"],
            "preferred_skills": parsed["preferred_skills"],
            "confidence_score": parsed["confidence_score"],
            "created_at": now_str,
            "updated_at": now_str,
            "candidate_count": 0,
            "role_intelligence": parsed["role_intelligence"],
            "embedding_metadata": _build_embedding_metadata(
                job_id,
                data.title,
                parsed["required_skills"],
                parsed["preferred_skills"],
            ),
        }

        try:
            _store_job_record(job_id, job_record, parsed["requirement_evidence"])
        except HireSenseException:
            raise
        except Exception as exc:
            raise HireSenseException(
                status_code=503,
                code="JOB_STORAGE_FAILED",
                message="Job profile could not be stored after parsing.",
                details={"job_id": job_id, "reason": str(exc)},
            ) from exc

        # Alert Hooks
        from app.modules.alerts.service import AlertService
        from app.common.schemas import AlertSeverity
        if job_record.get("parsing_status") == "FAILED":
            AlertService.trigger_alert(
                alert_type="JOB_PARSE_FAILED",
                condition_key=f"JOB_PARSE_FAILED:{job_id}",
                source_entity_id=job_id,
                title=f"Job parsing failed for job {job_id}",
                message="The job description could not be parsed into a valid job profile.",
                severity=AlertSeverity.HIGH,
                job_id=job_id
            )
        else:
            AlertService.clear_alert(f"JOB_PARSE_FAILED:{job_id}", "Job reprocess succeeded.")
            
        AlertService.clear_alert(f"STALE_PROFILE:JOB:{job_id}", "Job profile updated, no longer stale.")

        return JobResponseData(**job_record)

    @staticmethod
    def update_job(job_id: str, data: JobUpdate) -> JobResponseData:
        if job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} was not found."
            )

        job = dict(_jobs_db[job_id])
        if data.title is not None:
            job["title"] = _normalize_text(data.title)
        if data.location is not None:
            job["location"] = _normalize_text(data.location)
        if data.employment_type is not None:
            job["employment_type"] = _normalize_text(data.employment_type)
        if data.status is not None:
            job["status"] = data.status
        if data.description_text is not None:
            job["description_text"] = _normalize_text(data.description_text)

        if not job.get("title") or not job.get("description_text"):
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="Title and description_text are required."
            )

        parsed = _parse_job_description(
            JobCreate(
                title=job["title"],
                source_type=SourceType.TEXT,
                description_text=job["description_text"],
                location=job.get("location"),
                employment_type=job.get("employment_type"),
            )
        )
        now_str = _utc_now()
        job["required_skills"] = parsed["required_skills"]
        job["preferred_skills"] = parsed["preferred_skills"]
        job["confidence_score"] = parsed["confidence_score"]
        job["updated_at"] = now_str
        job["role_intelligence"] = parsed["role_intelligence"]
        job["requirement_version"] = int(job.get("requirement_version", 1)) + 1
        job["embedding_metadata"] = _build_embedding_metadata(
            job_id,
            job["title"],
            parsed["required_skills"],
            parsed["preferred_skills"],
        )
        job["embedding_metadata"]["status"] = "STALE"
        job["embedding_metadata"]["updated_at"] = now_str

        _store_job_record(job_id, job, parsed["requirement_evidence"])

        # Alert Hooks
        from app.modules.alerts.service import AlertService
        from app.common.schemas import AlertSeverity
        if job.get("parsing_status") == "FAILED":
            AlertService.trigger_alert(
                alert_type="JOB_PARSE_FAILED",
                condition_key=f"JOB_PARSE_FAILED:{job_id}",
                source_entity_id=job_id,
                title=f"Job parsing failed for job {job_id}",
                message="The job description could not be parsed into a valid job profile.",
                severity=AlertSeverity.HIGH,
                job_id=job_id
            )
        else:
            AlertService.clear_alert(f"JOB_PARSE_FAILED:{job_id}", "Job reprocess succeeded.")
            
        AlertService.clear_alert(f"STALE_PROFILE:JOB:{job_id}", "Job profile updated, no longer stale.")

        return JobResponseData(**job)

    @staticmethod
    def reprocess_job(job_id: str) -> JobResponseData:
        if job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} was not found."
            )

        job = dict(_jobs_db[job_id])
        description_text = job.get("description_text", "")
        if not description_text:
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="description_text is required for reprocessing."
            )

        parsed = _parse_job_description(
            JobCreate(
                title=job["title"],
                source_type=SourceType.TEXT,
                description_text=description_text,
                location=job.get("location"),
                employment_type=job.get("employment_type"),
            )
        )
        now_str = _utc_now()
        job["required_skills"] = parsed["required_skills"]
        job["preferred_skills"] = parsed["preferred_skills"]
        job["confidence_score"] = parsed["confidence_score"]
        job["updated_at"] = now_str
        job["role_intelligence"] = parsed["role_intelligence"]
        job["requirement_version"] = int(job.get("requirement_version", 1)) + 1
        job["embedding_metadata"] = _build_embedding_metadata(
            job_id,
            job["title"],
            parsed["required_skills"],
            parsed["preferred_skills"],
        )
        job["embedding_metadata"]["status"] = "STALE"
        job["embedding_metadata"]["updated_at"] = now_str

        _store_job_record(job_id, job, parsed["requirement_evidence"])

        # Alert Hooks
        from app.modules.alerts.service import AlertService
        from app.common.schemas import AlertSeverity
        if job.get("parsing_status") == "FAILED":
            AlertService.trigger_alert(
                alert_type="JOB_PARSE_FAILED",
                condition_key=f"JOB_PARSE_FAILED:{job_id}",
                source_entity_id=job_id,
                title=f"Job parsing failed for job {job_id}",
                message="The job description could not be parsed into a valid job profile.",
                severity=AlertSeverity.HIGH,
                job_id=job_id
            )
        else:
            AlertService.clear_alert(f"JOB_PARSE_FAILED:{job_id}", "Job reprocess succeeded.")
            
        AlertService.clear_alert(f"STALE_PROFILE:JOB:{job_id}", "Job profile updated, no longer stale.")

        return JobResponseData(**job)

    @staticmethod
    def list_jobs(
        status: Optional[str] = None,
        limit: int = 10,
        page_token: Optional[str] = None,
        created_after: Optional[str] = None
    ) -> Tuple[List[JobListItem], Optional[str]]:
        jobs = list(_jobs_db.values())
        jobs.sort(key=lambda job: (_parse_iso_timestamp(job["created_at"]), job["job_id"]), reverse=True)

        cursor_cutoff: Optional[Tuple[datetime, str]] = None
        if page_token:
            try:
                created_at_value, job_id_value = page_token.rsplit("|", 1)
                cursor_cutoff = (_parse_iso_timestamp(created_at_value), job_id_value)
            except Exception as exc:
                raise HireSenseException(
                    status_code=400,
                    code="INVALID_REQUEST",
                    message="page_token is invalid.",
                    details={"field": "page_token"},
                ) from exc

        created_after_cutoff: Optional[datetime] = None
        if created_after:
            try:
                created_after_cutoff = _parse_iso_timestamp(created_after)
            except Exception as exc:
                raise HireSenseException(
                    status_code=400,
                    code="INVALID_REQUEST",
                    message="created_after must be an ISO 8601 timestamp.",
                    details={"field": "created_after"},
                ) from exc

        items: List[JobListItem] = []
        next_page_token: Optional[str] = None
        for job in jobs:
            job_created_at = _parse_iso_timestamp(job["created_at"])
            if status and _enum_value(job["status"]) != status:
                continue
            if created_after_cutoff and job_created_at <= created_after_cutoff:
                continue
            if cursor_cutoff:
                cursor_time, cursor_job_id = cursor_cutoff
                if (job_created_at, job["job_id"]) >= (cursor_time, cursor_job_id):
                    continue
            items.append(JobListItem(
                job_id=job["job_id"],
                title=job["title"],
                status=job["status"],
                candidate_count=job.get("candidate_count", 0),
                created_at=job["created_at"]
            ))
            if len(items) == limit:
                break

        if len(items) == limit:
            last_item = items[-1]
            last_item_index = next(
                index for index, job in enumerate(jobs) if job["job_id"] == last_item.job_id
            )
            for candidate_job in jobs[last_item_index + 1:]:
                candidate_time = _parse_iso_timestamp(candidate_job["created_at"])
                if status and _enum_value(candidate_job["status"]) != status:
                    continue
                if created_after_cutoff and candidate_time <= created_after_cutoff:
                    continue
                if cursor_cutoff and (candidate_time, candidate_job["job_id"]) >= cursor_cutoff:
                    continue
                next_page_token = f"{last_item.created_at}|{last_item.job_id}"
                break

        return items, next_page_token

    @staticmethod
    def get_job(job_id: str) -> JobResponseData:
        if job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} was not found."
            )
        return JobResponseData(**_jobs_db[job_id])

    @staticmethod
    def get_requirements(job_id: str) -> Dict[str, Any]:
        if job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} was not found."
            )

        job = _jobs_db[job_id]
        return {
            "job_id": job["job_id"],
            "required_skills": job.get("required_skills", []),
            "preferred_skills": job.get("preferred_skills", []),
            "confidence_score": job.get("confidence_score", 0.0),
            "role_intelligence": job.get("role_intelligence", {}),
            "requirement_evidence": _job_requirements_db.get(job_id, []),
            "embedding_metadata": job.get("embedding_metadata", {}),
            "updated_at": job.get("updated_at"),
        }
