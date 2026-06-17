from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import re

from app.common.schemas import (
    CandidateCreate, CandidateUpdate, CandidateResponseData, 
    CandidateListItem, CandidateDetailData, CandidateEvidenceItem
)
from app.common.errors import HireSenseException
from app.common.skills import find_skills_in_text, _SKILL_ALIASES

# Simple in-memory DB for prototype stability
_candidates_db: Dict[str, Dict] = {
    "CAND_0000001": {
        "candidate_id": "CAND_0000001",
        "full_name": "Aarav Sharma",
        "normalized_skills": ["python", "fastapi", "postgresql"],
        "years_of_experience": 5.4,
        "confidence_score": 0.89,
        "behavioral_signals": ["ownership", "mentorship"],
        "created_at": "2026-05-27T15:00:00Z",
        "updated_at": "2026-05-27T15:08:00Z",
        "profile": {
            "full_name": "Aarav Sharma",
            "email": "aarav@example.com",
            "phone": None,
            "location": None
        },
        "career_history": [
            {
                "job_title": "Software Engineer",
                "organization": "Tech Solutions",
                "duration_years": 5.4,
                "description": "Developed and maintained FastAPI services with PostgreSQL backends."
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "institution": "University of Technology",
                "completion_year": 2018
            }
        ],
        "skills": ["python", "fastapi", "postgresql"],
        "redrob_signals": ["ownership", "mentorship"],
        "embedding_metadata": {
            "entity_type": "CANDIDATE",
            "entity_id": "CAND_0000001",
            "embedding_version": "candidate_profile_v1",
            "status": "READY",
            "source_text": "Aarav Sharma python fastapi postgresql ownership mentorship",
            "updated_at": "2026-05-27T15:08:00Z"
        }
    }
}

_candidate_evidence_db: Dict[str, List[Dict[str, Any]]] = {
    "CAND_0000001": [
        {
            "candidate_experience_evidence_id": "ev_0000001",
            "candidate_id": "CAND_0000001",
            "evidence_type": "SKILL",
            "canonical_value": "python",
            "source_text": "python",
            "source_span_start": 30,
            "source_span_end": 36,
            "created_at": "2026-05-27T15:08:00Z"
        }
    ]
}

_candidate_counter = 1
_evidence_counter = 1

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _parse_iso_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)

def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def _generate_mock_resume_text(full_name: str, email: Optional[str], resume_file_name: Optional[str]) -> str:
    fname = (resume_file_name or "").lower()
    email_str = email or f"{full_name.lower().replace(' ', '.')}@example.com"
    
    skills_mentioned = ["Python"]
    experience_years = "3.5"
    signals = ["collaboration"]
    
    if "resume" in fname:
        skills_mentioned.extend(["FastAPI", "PostgreSQL"])
        experience_years = "5.4"
        signals.extend(["ownership", "mentorship"])
    if "react" in fname:
        skills_mentioned.append("React")
        experience_years = "4.0"
        signals.append("ownership")
    if "java" in fname:
        skills_mentioned.append("Java")
        experience_years = "3.0"
        signals.append("mentorship")
        
    skills_line = ", ".join(skills_mentioned)
    signals_description = ""
    if "ownership" in signals:
        signals_description += " I take full ownership of the backend deployments."
    if "mentorship" in signals:
        signals_description += " Mentored junior engineers and guided system architecture."
    if "collaboration" in signals:
        signals_description += " Strong history of collaboration across cross-functional product teams."
        
    text = (
        f"Resume profile for {full_name}. Contact: {email_str}.\n"
        f"Education: Bachelor of Science in Computer Science, University of Technology, 2018.\n"
        f"Experience: Worked for {experience_years} years as a Software Engineer.\n"
        f"Technical Skills: Proficient in {skills_line}.\n"
        f"Professional signals:{signals_description}"
    )
    return text

def _parse_candidate_profile(
    candidate_id: str, 
    full_name: str, 
    email: Optional[str], 
    text: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    now_str = _utc_now()
    skills_found = find_skills_in_text(text)
    evidence: List[Dict[str, Any]] = []
    
    global _evidence_counter
    
    for skill in skills_found:
        match = re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE)
        if not match:
            for alias in _SKILL_ALIASES.get(skill, []):
                match = re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE)
                if match:
                    break
        
        span_start = match.start() if match else 0
        span_end = match.end() if match else 0
        source_text = text[span_start:span_end] if match else skill
        
        _evidence_counter += 1
        evidence.append({
            "candidate_experience_evidence_id": f"ev_{_evidence_counter:07d}",
            "candidate_id": candidate_id,
            "evidence_type": "SKILL",
            "canonical_value": skill,
            "source_text": source_text,
            "source_span_start": span_start,
            "source_span_end": span_end,
            "created_at": now_str
        })

    years_match = re.search(r"Worked for (\d+(?:\.\d+)?) years", text)
    years_of_experience = float(years_match.group(1)) if years_match else 3.5

    redrob_signals = []
    behavioral_cues = {
        "ownership": ["ownership", "took ownership", "own"],
        "mentorship": ["mentorship", "mentored", "guide"],
        "collaboration": ["collaboration", "collaborated", "team player"],
        "innovation": ["innovation", "innovated", "designed"]
    }
    
    for signal, cues in behavioral_cues.items():
        for cue in cues:
            match = re.search(rf"\b{re.escape(cue)}\b", text, re.IGNORECASE)
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

    education = []
    edu_match = re.search(r"Education:\s*(.*?),\s*(.*?),\s*(\d{4})", text)
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
        start = edu_full_match.start() if edu_full_match else 0
        end = edu_full_match.end() if edu_full_match else 0
        _evidence_counter += 1
        evidence.append({
            "candidate_experience_evidence_id": f"ev_{_evidence_counter:07d}",
            "candidate_id": candidate_id,
            "evidence_type": "EXPERIENCE",
            "canonical_value": degree,
            "source_text": text[start:end].strip() if edu_full_match else degree,
            "source_span_start": start,
            "source_span_end": end,
            "created_at": now_str
        })
    else:
        education.append({
            "degree": "CS Degree",
            "institution": "Not Specified",
            "completion_year": None
        })

    career_history = []
    history_match = re.search(r"Worked for (\d+(?:\.\d+)?) years as a (.*?)\.", text)
    if history_match:
        role = history_match.group(2).strip()
        career_history.append({
            "job_title": role,
            "organization": "Tech Solutions",
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
    else:
        career_history.append({
            "job_title": "Software Engineer",
            "organization": "Not Specified",
            "duration_years": years_of_experience,
            "description": f"Worked as Software Engineer for {years_of_experience} years."
        })

    confidence_score = 0.50
    if email:
        confidence_score += 0.10
    if skills_found:
        confidence_score += 0.15
    if redrob_signals:
        confidence_score += 0.10
    if career_history:
        confidence_score += 0.10
    score = min(max(confidence_score, 0.1), 0.95)

    profile = {
        "full_name": full_name,
        "email": email or f"{full_name.lower().replace(' ', '.')}@example.com",
        "phone": None,
        "location": None
    }

    parsed_data = {
        "profile": profile,
        "career_history": career_history,
        "education": education,
        "skills": skills_found,
        "redrob_signals": redrob_signals,
        "years_of_experience": years_of_experience,
        "confidence_score": round(score, 2)
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

class CandidateService:
    @staticmethod
    def create_candidate(data: CandidateCreate) -> CandidateResponseData:
        global _candidate_counter
        if not data.full_name or not data.full_name.strip():
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="Full name is required."
            )
        
        _candidate_counter += 1
        candidate_id = f"CAND_{_candidate_counter:07d}"
        
        # Ingest: generate mock resume text and parse it
        text_content = _generate_mock_resume_text(data.full_name, data.email, data.resume_file_name)
        parsed, evidence = _parse_candidate_profile(candidate_id, data.full_name, data.email, text_content)
        
        now_str = _utc_now()
        cand_record = {
            "candidate_id": candidate_id,
            "full_name": data.full_name,
            "normalized_skills": parsed["skills"],
            "years_of_experience": parsed["years_of_experience"],
            "confidence_score": parsed["confidence_score"],
            "created_at": now_str,
            "updated_at": now_str,
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
        return CandidateResponseData(**cand_record)

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
        cand["embedding_metadata"] = _build_embedding_metadata(
            candidate_id,
            cand["full_name"],
            cand["normalized_skills"],
            cand["redrob_signals"]
        )
        cand["embedding_metadata"]["status"] = "STALE"
        cand["embedding_metadata"]["updated_at"] = now_str
        
        _candidates_db[candidate_id] = cand
        return CandidateResponseData(**cand)

    @staticmethod
    def list_candidates(
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        page_token: Optional[str] = None
    ) -> List[CandidateListItem]:
        items = []
        for cand in _candidates_db.values():
            items.append(CandidateListItem(
                candidate_id=cand["candidate_id"],
                full_name=cand["full_name"],
                confidence_score=cand["confidence_score"],
                updated_at=cand["updated_at"]
            ))
        return items[:limit]

    @staticmethod
    def get_candidate(candidate_id: str) -> CandidateResponseData:
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
        return CandidateResponseData(**_candidates_db[candidate_id])

    @staticmethod
    def get_candidate_detail(candidate_id: str) -> CandidateDetailData:
        if candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {candidate_id} was not found."
            )
        cand = _candidates_db[candidate_id]
        return CandidateDetailData(
            candidate_id=cand["candidate_id"],
            full_name=cand["full_name"],
            normalized_skills=cand["normalized_skills"],
            behavioral_signals=cand.get("behavioral_signals", []),
            updated_at=cand["updated_at"],
            profile=cand.get("profile", {}),
            career_history=cand.get("career_history", []),
            education=cand.get("education", []),
            skills=cand.get("skills", []),
            redrob_signals=cand.get("redrob_signals", []),
            embedding_metadata=cand.get("embedding_metadata", {})
        )

    @staticmethod
    def get_resume_evidence(candidate_id: str) -> List[CandidateEvidenceItem]:
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
        email = cand["profile"].get("email")
        resume_file_name = cand["embedding_metadata"].get("entity_id") # dummy lookup or metadata
        
        # Ingest: generate mock resume text and parse it
        text_content = _generate_mock_resume_text(full_name, email, resume_file_name)
        parsed, evidence = _parse_candidate_profile(candidate_id, full_name, email, text_content)
        
        now_str = _utc_now()
        updated_cand = {
            "candidate_id": candidate_id,
            "full_name": full_name,
            "normalized_skills": parsed["skills"],
            "years_of_experience": parsed["years_of_experience"],
            "confidence_score": parsed["confidence_score"],
            "created_at": cand["created_at"],
            "updated_at": now_str,
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
        return CandidateResponseData(**updated_cand)
