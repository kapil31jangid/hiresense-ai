from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import re

from app.common.schemas import (
    CandidateCreate, CandidateUpdate, CandidateResponseData,
    CandidateListItem, CandidateDetailData, CandidateEvidenceItem
)
from app.common.errors import HireSenseException
from app.common.skills import find_skills_in_text, _SKILL_ALIASES, normalize_skill
from app.common.repositories import FirestoreBackedStore, FirestoreBackedListStore
from app.challenge import dataset_store as challenge_dataset

_candidates_db: Dict[str, Dict] = FirestoreBackedStore("candidates", {})
_candidate_evidence_db: Dict[str, List[Dict[str, Any]]] = FirestoreBackedListStore("candidate_evidence", {})

_candidate_counter = 0
_evidence_counter = 0

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _parse_iso_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)

def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def _extract_text_from_bytes(file_bytes: bytes) -> str:
    if not file_bytes:
        return ""

    decoded = file_bytes.decode("utf-8", errors="ignore")
    decoded = _normalize_text(decoded)
    if len(decoded) >= 40:
        return decoded

    printable_chunks = re.findall(rb"[ -~]{4,}", file_bytes)
    ascii_text = _normalize_text(" ".join(chunk.decode("ascii", errors="ignore") for chunk in printable_chunks))
    return ascii_text or decoded


def _canonicalize_skill_list(skills: Optional[List[str]], source_text: str = "") -> List[str]:
    canonical: List[str] = []
    for skill in skills or []:
        normalized = normalize_skill(skill) or skill.strip().lower()
        if normalized and normalized not in canonical:
            canonical.append(normalized)
    if source_text:
        for found_skill in find_skills_in_text(source_text):
            if found_skill not in canonical:
                canonical.append(found_skill)
    return canonical


def _parse_structured_source_data(source_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    source_data = source_data or {}
    profile = source_data.get("profile") or {}
    career_history = source_data.get("career_history") or []
    education = source_data.get("education") or []
    skills = _canonicalize_skill_list(source_data.get("skills"), _normalize_text(
        " ".join([
            _normalize_text(str(profile.get("summary", ""))),
            _normalize_text(str(source_data.get("summary", ""))),
        ])
    ))
    redrob_signals = _canonicalize_skill_list(source_data.get("redrob_signals"), "")
    years_of_experience = source_data.get("years_of_experience")
    if years_of_experience is None:
        years_of_experience = source_data.get("experience_years")
    if years_of_experience is None:
        years_of_experience = 0.0
    try:
        years_of_experience = float(years_of_experience)
    except (TypeError, ValueError):
        years_of_experience = 0.0

    return {
        "profile": profile,
        "career_history": career_history,
        "education": education,
        "skills": skills,
        "redrob_signals": redrob_signals,
        "years_of_experience": years_of_experience,
    }


def _build_candidate_source_text(
    data: CandidateCreate,
    source_text: Optional[str] = None,
    source_bytes: Optional[bytes] = None,
) -> str:
    structured_parts: List[str] = []
    
    if source_text:
        structured_parts.append(_normalize_text(source_text))
    elif source_bytes:
        extracted = _extract_text_from_bytes(source_bytes)
        if extracted:
            structured_parts.append(extracted)

    if data.source_data:
        profile = data.source_data.get("profile") or {}
        for key in ("summary", "headline", "bio"):
            if data.source_data.get(key):
                structured_parts.append(str(data.source_data.get(key)))
            if profile.get(key):
                structured_parts.append(str(profile.get(key)))
        for section_name in ("career_history", "education", "skills", "redrob_signals"):
            section_value = data.source_data.get(section_name)
            if section_value:
                structured_parts.append(str(section_value))

    if data.full_name:
        structured_parts.append(f"Name: {data.full_name}")
    if data.email:
        structured_parts.append(f"Email: {data.email}")
    if data.resume_file_name:
        structured_parts.append(f"File: {data.resume_file_name}")

    return _normalize_text(" ".join(structured_parts))


def _parse_candidate_profile(
    candidate_id: str,
    full_name: str,
    email: Optional[str],
    text: str,
    source_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    now_str = _utc_now()
    structured = _parse_structured_source_data(source_data)
    skills_found = _canonicalize_skill_list(structured["skills"], text)
    evidence: List[Dict[str, Any]] = []
    parsing_status = "COMPLETED"
    
    global _evidence_counter
    
    for skill in skills_found:
        match = re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE) if text else None
        if not match:
            for alias in _SKILL_ALIASES.get(skill, []):
                if text:
                    match = re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE)
                if match:
                    break

        span_start = match.start() if match else None
        span_end = match.end() if match else None
        source_value = text[span_start:span_end] if match and span_start is not None and span_end is not None else skill

        _evidence_counter += 1
        evidence.append({
            "candidate_experience_evidence_id": f"ev_{_evidence_counter:07d}",
            "candidate_id": candidate_id,
            "evidence_type": "SKILL",
            "canonical_value": skill,
            "source_text": source_value,
            "source_span_start": span_start,
            "source_span_end": span_end,
            "created_at": now_str
        })

    years_match = re.search(r"(?:Worked for|Experience: worked for)\s+(\d+(?:\.\d+)?)\s+years", text, re.IGNORECASE)
    years_of_experience = float(years_match.group(1)) if years_match else structured["years_of_experience"]

    redrob_signals = list(structured["redrob_signals"])
    behavioral_cues = {
        "ownership": ["ownership", "took ownership", "own"],
        "mentorship": ["mentorship", "mentored", "guide"],
        "collaboration": ["collaboration", "collaborated", "team player"],
        "innovation": ["innovation", "innovated", "designed"]
    }
    
    for signal, cues in behavioral_cues.items():
        for cue in cues:
            match = re.search(rf"\b{re.escape(cue)}\b", text, re.IGNORECASE) if text else None
            if match:
                redrob_signals.append(signal)
                _evidence_counter += 1
                evidence.append({
                    "candidate_experience_evidence_id": f"ev_{_evidence_counter:07d}",
                    "candidate_id": candidate_id,
                    "evidence_type": "BEHAVIORAL_SIGNAL",
                    "canonical_value": signal,
                    "source_text": text[max(0, match.start() - 15):min(len(text), match.end() + 15)].strip(),
                    "source_span_start": match.start(),
                    "source_span_end": match.end(),
                    "created_at": now_str
                })
                break
        else:
            continue

    if not text and (skills_found or redrob_signals or structured["career_history"] or structured["education"]):
        parsing_status = "PARTIAL"
    elif not text:
        parsing_status = "PARTIAL"

    education = structured["education"]
    if not education:
        edu_match = re.search(r"Education:\s*(.*?),\s*(.*?),\s*(\d{4})", text, re.IGNORECASE)
        if edu_match:
            degree = edu_match.group(1).strip()
            institution = edu_match.group(2).strip()
            completion_year = int(edu_match.group(3))
            education.append({
                "degree": degree,
                "institution": institution,
                "completion_year": completion_year
            })

            edu_full_match = re.search(r"Education:\s*(.*?)\n", text)
            start = edu_full_match.start() if edu_full_match else None
            end = edu_full_match.end() if edu_full_match else None
            _evidence_counter += 1
            evidence.append({
                "candidate_experience_evidence_id": f"ev_{_evidence_counter:07d}",
                "candidate_id": candidate_id,
                "evidence_type": "EDUCATION",
                "canonical_value": degree,
                "source_text": text[start:end].strip() if edu_full_match else degree,
                "source_span_start": start,
                "source_span_end": end,
                "created_at": now_str
            })

    career_history = structured["career_history"]
    if not career_history:
        history_match = re.search(r"Worked for (\d+(?:\.\d+)?) years as a (.*?)\.", text, re.IGNORECASE)
        if history_match:
            role = history_match.group(2).strip()
            career_history.append({
                "job_title": role,
                "organization": "Not Specified",
                "duration_years": years_of_experience,
                "description": f"Worked for {years_of_experience} years as a {role}."
            })

            start = history_match.start()
            end = history_match.end()
            _evidence_counter += 1
            evidence.append({
                "candidate_experience_evidence_id": f"ev_{_evidence_counter:07d}",
                "candidate_id": candidate_id,
                "evidence_type": "EXPERIENCE",
                "canonical_value": role,
                "source_text": text[start:end],
                "source_span_start": start,
                "source_span_end": end,
                "created_at": now_str
            })

    profile = dict(structured["profile"])
    profile["full_name"] = full_name
    profile["email"] = email or profile.get("email") or f"{full_name.lower().replace(' ', '.')}@example.com"
    profile.setdefault("phone", None)
    profile.setdefault("location", None)

    confidence_score = 0.30
    if email or profile.get("email"):
        confidence_score += 0.10
    if skills_found:
        confidence_score += 0.20
    if redrob_signals:
        confidence_score += 0.10
    if career_history:
        confidence_score += 0.10
    if education:
        confidence_score += 0.05
    if structured["career_history"] or structured["education"] or structured["skills"] or structured["redrob_signals"]:
        confidence_score += 0.10
    if parsing_status == "PARTIAL":
        confidence_score -= 0.05
    score = min(max(confidence_score, 0.1), 0.95)

    parsed_data = {
        "profile": profile,
        "career_history": career_history,
        "education": education,
        "skills": skills_found,
        "redrob_signals": redrob_signals,
        "years_of_experience": years_of_experience,
        "confidence_score": round(score, 2),
        "parsing_status": parsing_status,
    }

    return parsed_data, evidence

def _build_embedding_metadata(candidate_id: str, full_name: str, skills: List[str], signals: List[str]) -> Dict[str, Any]:
    structured_text = " ".join([full_name, " ".join(skills), " ".join(signals)]).strip()
    return {
        "entity_type": "CANDIDATE",
        "entity_id": candidate_id,
        "embedding_version": "candidate_profile_v1",
        "status": "STALE",
        "source_text": structured_text,
    }


def _candidate_record_to_response(candidate_record: Dict[str, Any]) -> CandidateResponseData:
    return CandidateResponseData(
        candidate_id=candidate_record["candidate_id"],
        full_name=candidate_record["full_name"],
        normalized_skills=candidate_record.get("normalized_skills", []),
        years_of_experience=candidate_record.get("years_of_experience", 0.0),
        confidence_score=candidate_record.get("confidence_score", 0.0),
        parsing_status=candidate_record.get("parsing_status", "PARTIAL"),
        created_at=candidate_record["created_at"],
        updated_at=candidate_record["updated_at"],
        profile=candidate_record.get("profile", {}),
        career_history=candidate_record.get("career_history", []),
        education=candidate_record.get("education", []),
        skills=candidate_record.get("skills", []),
        redrob_signals=candidate_record.get("redrob_signals", []),
        embedding_metadata=candidate_record.get("embedding_metadata", {}),
    )


def _candidate_record_to_detail(candidate_record: Dict[str, Any]) -> CandidateDetailData:
    return CandidateDetailData(
        candidate_id=candidate_record["candidate_id"],
        full_name=candidate_record["full_name"],
        normalized_skills=candidate_record.get("normalized_skills", []),
        behavioral_signals=candidate_record.get("behavioral_signals", []),
        parsing_status=candidate_record.get("parsing_status", "PARTIAL"),
        updated_at=candidate_record["updated_at"],
        profile=candidate_record.get("profile", {}),
        career_history=candidate_record.get("career_history", []),
        education=candidate_record.get("education", []),
        skills=candidate_record.get("skills", []),
        redrob_signals=candidate_record.get("redrob_signals", []),
        embedding_metadata=candidate_record.get("embedding_metadata", {}),
    )

class CandidateService:
    @staticmethod
    def create_candidate(
        data: CandidateCreate,
        source_text: Optional[str] = None,
        source_file_name: Optional[str] = None,
    ) -> CandidateResponseData:
        global _candidate_counter
        if not data.full_name or not data.full_name.strip():
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="Full name is required."
            )
        
        _candidate_counter += 1
        candidate_id = f"CAND_{_candidate_counter:07d}"

        explicit_source_present = bool(source_text or data.source_text or data.source_data or source_file_name or data.resume_file_name)
        effective_source_text = _build_candidate_source_text(
            data,
            source_text=source_text or data.source_text,
        )
        if not effective_source_text and data.source_type == "TEXT":
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="source_text is required when source_type is TEXT.",
                details={"field": "source_text"},
            )

        parsed, evidence = _parse_candidate_profile(
            candidate_id,
            data.full_name,
            data.email,
            effective_source_text,
            source_data=data.source_data,
        )
        if not explicit_source_present:
            parsed["parsing_status"] = "PARTIAL"
        
        now_str = _utc_now()
        cand_record = {
            "candidate_id": candidate_id,
            "full_name": data.full_name,
            "normalized_skills": parsed["skills"],
            "years_of_experience": parsed["years_of_experience"],
            "confidence_score": parsed["confidence_score"],
            "parsing_status": parsed["parsing_status"],
            "created_at": now_str,
            "updated_at": now_str,
            "source_type": data.source_type,
            "source_file_name": source_file_name or data.resume_file_name,
            "source_text": effective_source_text,
            "source_data": data.source_data or {},
            "profile": parsed["profile"],
            "career_history": parsed["career_history"],
            "education": parsed["education"],
            "skills": parsed["skills"],
            "redrob_signals": parsed["redrob_signals"],
            "behavioral_signals": parsed["redrob_signals"],
            "embedding_metadata": _build_embedding_metadata(
                candidate_id,
                data.full_name,
                parsed["skills"],
                parsed["redrob_signals"]
            )
        }
        
        _candidates_db[candidate_id] = cand_record
        _candidate_evidence_db[candidate_id] = evidence
        
        # Alert Hooks
        from app.modules.alerts.service import AlertService
        from app.common.schemas import AlertSeverity
        if cand_record["parsing_status"] == "FAILED":
            AlertService.trigger_alert(
                alert_type="RESUME_PARSE_FAILED",
                condition_key=f"RESUME_PARSE_FAILED:{candidate_id}",
                source_entity_id=candidate_id,
                title=f"Resume parsing failed for candidate {candidate_id}",
                message="The resume file could not be parsed into a valid candidate profile.",
                severity=AlertSeverity.HIGH,
                candidate_id=candidate_id
            )
        else:
            AlertService.clear_alert(f"RESUME_PARSE_FAILED:{candidate_id}", "Reprocess succeeded.")
            
        AlertService.clear_alert(f"STALE_PROFILE:CANDIDATE:{candidate_id}", "Candidate profile updated, no longer stale.")
        
        return _candidate_record_to_response(cand_record)

    @staticmethod
    def update_candidate(candidate_id: str, data: CandidateUpdate) -> CandidateResponseData:
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
            
        cand = dict(_candidates_db[candidate_id])
        
        if data.full_name is not None:
            cand["full_name"] = data.full_name
            cand["profile"]["full_name"] = data.full_name
        if data.email is not None:
            cand["profile"]["email"] = data.email
        if data.normalized_skills is not None:
            cand["normalized_skills"] = data.normalized_skills
            cand["skills"] = data.normalized_skills
        if data.years_of_experience is not None:
            cand["years_of_experience"] = data.years_of_experience
        if data.confidence_score is not None:
            cand["confidence_score"] = data.confidence_score
        if data.profile is not None:
            cand["profile"].update(data.profile)
        if data.career_history is not None:
            cand["career_history"] = data.career_history
        if data.education is not None:
            cand["education"] = data.education
        if data.skills is not None:
            cand["skills"] = data.skills
            cand["normalized_skills"] = data.skills
        if data.redrob_signals is not None:
            cand["redrob_signals"] = data.redrob_signals
            cand["behavioral_signals"] = data.redrob_signals

        now_str = _utc_now()
        cand["updated_at"] = now_str
        cand["parsing_status"] = "PARTIAL" if not cand.get("source_text") else cand.get("parsing_status", "COMPLETED")
        cand["embedding_metadata"] = _build_embedding_metadata(
            candidate_id,
            cand["full_name"],
            cand["normalized_skills"],
            cand["redrob_signals"]
        )
        cand["embedding_metadata"]["status"] = "STALE"
        cand["embedding_metadata"]["updated_at"] = now_str
        
        _candidates_db[candidate_id] = cand
        
        # Alert Hooks
        from app.modules.alerts.service import AlertService
        from app.common.schemas import AlertSeverity
        if cand.get("parsing_status") == "FAILED":
            AlertService.trigger_alert(
                alert_type="RESUME_PARSE_FAILED",
                condition_key=f"RESUME_PARSE_FAILED:{candidate_id}",
                source_entity_id=candidate_id,
                title=f"Resume parsing failed for candidate {candidate_id}",
                message="The resume file could not be parsed into a valid candidate profile.",
                severity=AlertSeverity.HIGH,
                candidate_id=candidate_id
            )
        else:
            AlertService.clear_alert(f"RESUME_PARSE_FAILED:{candidate_id}", "Reprocess succeeded.")
            
        AlertService.clear_alert(f"STALE_PROFILE:CANDIDATE:{candidate_id}", "Candidate profile updated, no longer stale.")
        
        return _candidate_record_to_response(cand)

    @staticmethod
    def list_candidates(
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        page_token: Optional[str] = None
    ) -> Tuple[List[CandidateListItem], Optional[str]]:
        challenge_candidates = challenge_dataset.list_summaries()
        if challenge_candidates:
            # In challenge dataset mode, the organizer dataset is the only candidate
            # source of truth. Do not merge local demo/manual records because they
            # can duplicate names and confuse ranking/export validation.
            candidates = challenge_candidates
            candidates.sort(key=lambda cand: cand["candidate_id"])
            start_index = 0
            if page_token:
                candidate_ids = [candidate["candidate_id"] for candidate in candidates]
                try:
                    start_index = candidate_ids.index(page_token) + 1
                except ValueError:
                    raise HireSenseException(
                        status_code=400,
                        code="INVALID_REQUEST",
                        message="page_token is invalid.",
                        details={"field": "page_token"},
                    )

            filtered_candidates = [
                candidate for candidate in candidates[start_index:]
                if (not status or candidate.get("parsing_status") == status)
                and (not job_id or job_id in candidate.get("profile", {}).get("job_ids", []))
            ]
            page = filtered_candidates[:limit]
            next_page_token = page[-1]["candidate_id"] if len(filtered_candidates) > limit and page else None
            return [
                CandidateListItem(
                    candidate_id=cand["candidate_id"],
                    full_name=cand["full_name"],
                    confidence_score=cand["confidence_score"],
                    parsing_status=cand.get("parsing_status", "PARTIAL"),
                    updated_at=cand["updated_at"]
                )
                for cand in page
            ], next_page_token
        else:
            candidates = list(_candidates_db.values())
            candidates.sort(key=lambda cand: (_parse_iso_timestamp(cand["updated_at"]), cand["candidate_id"]), reverse=True)

        cursor_cutoff: Optional[Tuple[datetime, str]] = None
        if page_token:
            try:
                updated_at_value, candidate_id_value = page_token.rsplit("|", 1)
                cursor_cutoff = (_parse_iso_timestamp(updated_at_value), candidate_id_value)
            except Exception as exc:
                raise HireSenseException(
                    status_code=400,
                    code="INVALID_REQUEST",
                    message="page_token is invalid.",
                    details={"field": "page_token"},
                ) from exc

        items: List[CandidateListItem] = []
        next_page_token: Optional[str] = None
        for cand in candidates:
            updated_at = _parse_iso_timestamp(cand["updated_at"])
            if status and cand.get("parsing_status") != status:
                continue
            if job_id and job_id not in cand.get("profile", {}).get("job_ids", []):
                continue
            if cursor_cutoff and (updated_at, cand["candidate_id"]) >= cursor_cutoff:
                continue
            items.append(CandidateListItem(
                candidate_id=cand["candidate_id"],
                full_name=cand["full_name"],
                confidence_score=cand["confidence_score"],
                parsing_status=cand.get("parsing_status", "PARTIAL"),
                updated_at=cand["updated_at"]
            ))
            if len(items) == limit:
                break

        if len(items) == limit:
            next_page_token = f"{items[-1].updated_at}|{items[-1].candidate_id}"

        return items, next_page_token

    @staticmethod
    def get_candidate(candidate_id: str) -> CandidateResponseData:
        challenge_record = challenge_dataset.get_candidate(candidate_id)
        if challenge_record is not None:
            return _candidate_record_to_response(challenge_record)
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
        return _candidate_record_to_response(_candidates_db[candidate_id])

    @staticmethod
    def get_candidate_detail(candidate_id: str) -> CandidateDetailData:
        challenge_record = challenge_dataset.get_candidate(candidate_id)
        if challenge_record is not None:
            return _candidate_record_to_detail(challenge_record)
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
        cand = _candidates_db[candidate_id]
        return _candidate_record_to_detail(cand)

    @staticmethod
    def get_resume_evidence(candidate_id: str) -> List[CandidateEvidenceItem]:
        challenge_record = challenge_dataset.get_candidate(candidate_id)
        if challenge_record is not None:
            now_str = _utc_now()
            return [
                CandidateEvidenceItem(
                    candidate_experience_evidence_id=f"challenge_{candidate_id}_{idx:03d}",
                    candidate_id=candidate_id,
                    evidence_type="SKILL",
                    canonical_value=skill,
                    source_text=skill,
                    created_at=now_str,
                )
                for idx, skill in enumerate(challenge_record.get("normalized_skills", [])[:25], start=1)
            ]
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
        raw_evidence = _candidate_evidence_db.get(candidate_id, [])
        return [CandidateEvidenceItem(**item) for item in raw_evidence]

    @staticmethod
    def reprocess_candidate(candidate_id: str) -> CandidateResponseData:
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
            
        cand = _candidates_db[candidate_id]
        full_name = cand["full_name"]
        email = cand.get("profile", {}).get("email")
        source_text = cand.get("source_text", "")
        source_data = cand.get("source_data", {})
        parsed, evidence = _parse_candidate_profile(candidate_id, full_name, email, source_text, source_data=source_data)
        
        now_str = _utc_now()
        updated_cand = {
            "candidate_id": candidate_id,
            "full_name": full_name,
            "normalized_skills": parsed["skills"],
            "years_of_experience": parsed["years_of_experience"],
            "confidence_score": parsed["confidence_score"],
            "parsing_status": parsed["parsing_status"],
            "created_at": cand["created_at"],
            "updated_at": now_str,
            "source_type": cand.get("source_type", "TEXT"),
            "source_file_name": cand.get("source_file_name"),
            "source_text": source_text,
            "source_data": source_data,
            "profile": parsed["profile"],
            "career_history": parsed["career_history"],
            "education": parsed["education"],
            "skills": parsed["skills"],
            "redrob_signals": parsed["redrob_signals"],
            "behavioral_signals": parsed["redrob_signals"],
            "embedding_metadata": _build_embedding_metadata(
                candidate_id,
                full_name,
                parsed["skills"],
                parsed["redrob_signals"]
            )
        }
        updated_cand["embedding_metadata"]["status"] = "STALE"
        updated_cand["embedding_metadata"]["updated_at"] = now_str
        
        _candidates_db[candidate_id] = updated_cand
        _candidate_evidence_db[candidate_id] = evidence
        
        # Alert Hooks
        from app.modules.alerts.service import AlertService
        from app.common.schemas import AlertSeverity
        if updated_cand["parsing_status"] == "FAILED":
            AlertService.trigger_alert(
                alert_type="RESUME_PARSE_FAILED",
                condition_key=f"RESUME_PARSE_FAILED:{candidate_id}",
                source_entity_id=candidate_id,
                title=f"Resume parsing failed for candidate {candidate_id}",
                message="The resume file could not be parsed into a valid candidate profile.",
                severity=AlertSeverity.HIGH,
                candidate_id=candidate_id
            )
        else:
            AlertService.clear_alert(f"RESUME_PARSE_FAILED:{candidate_id}", "Reprocess succeeded.")
            
        AlertService.clear_alert(f"STALE_PROFILE:CANDIDATE:{candidate_id}", "Candidate profile updated, no longer stale.")
        
        return _candidate_record_to_response(updated_cand)
