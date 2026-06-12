from typing import List, Optional, Dict
from datetime import datetime
import re

from app.common.schemas import CandidateCreate, CandidateResponseData, CandidateListItem, CandidateDetailData
from app.common.errors import HireSenseException

_candidates_db: Dict[str, Dict] = {
    "CAND_0000001": {
        "candidate_id": "CAND_0000001",
        "full_name": "Aarav Sharma",
        "normalized_skills": ["python", "fastapi", "postgresql"],
        "years_of_experience": 5.4,
        "confidence_score": 0.89,
        "behavioral_signals": ["ownership", "mentorship"],
        "created_at": "2026-05-27T15:00:00Z",
        "updated_at": "2026-05-27T15:08:00Z"
    }
}
_candidate_counter = 1

class CandidateService:
    @staticmethod
    def create_candidate(data: CandidateCreate) -> CandidateResponseData:
        global _candidate_counter
        if not data.full_name.strip():
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="Full name is required."
            )
        
        # Determine skills from filename if file mode
        skills = ["python"]
        if data.resume_file_name:
            fname = data.resume_file_name.lower()
            if "resume" in fname:
                skills.extend(["fastapi", "postgresql"])
            if "java" in fname:
                skills.append("java")
            if "react" in fname:
                skills.append("react")

        _candidate_counter += 1
        candidate_id = f"CAND_{_candidate_counter:07d}"
        
        now_str = datetime.utcnow().isoformat() + "Z"
        cand_record = {
            "candidate_id": candidate_id,
            "full_name": data.full_name,
            "normalized_skills": list(set(skills)),
            "years_of_experience": 3.5,
            "confidence_score": 0.85,
            "behavioral_signals": ["collaboration"],
            "created_at": now_str,
            "updated_at": now_str
        }
        
        _candidates_db[candidate_id] = cand_record
        return CandidateResponseData(**cand_record)

    @staticmethod
    def list_candidates(
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        page_token: Optional[str] = None
    ) -> List[CandidateListItem]:
        items = []
        for cand in _candidates_db.values():
            # In a real app, job_id filtering would check applicant links. Here, we just list them.
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
            updated_at=cand["updated_at"]
        )
