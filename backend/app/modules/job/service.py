from typing import List, Optional, Dict
from datetime import datetime
import re

from app.common.schemas import JobCreate, JobResponseData, JobListItem, JobStatus
from app.common.errors import HireSenseException

# Simple in-memory DB for prototype stability
_jobs_db: Dict[str, Dict] = {
    "JOB_0000001": {
        "job_id": "JOB_0000001",
        "title": "Senior Backend Engineer",
        "status": JobStatus.ACTIVE,
        "required_skills": ["python", "fastapi", "postgresql"],
        "preferred_skills": ["distributed_systems"],
        "confidence_score": 0.93,
        "created_at": "2026-05-27T14:30:00Z",
        "updated_at": "2026-05-27T14:45:00Z",
        "candidate_count": 42
    }
}
_job_counter = 1

class JobService:
    @staticmethod
    def create_job(data: JobCreate) -> JobResponseData:
        global _job_counter
        # Basic validation
        if not data.title.strip() or not data.description_text.strip():
            raise HireSenseException(
                status_code=400,
                code="INVALID_REQUEST",
                message="Title and description_text are required."
            )
        
        # Simple skill parsing from text
        desc = data.description_text.lower()
        skills_map = ["python", "fastapi", "postgresql", "spacy", "faiss", "react", "next.js", "docker", "aws"]
        required = []
        preferred = []
        
        for skill in skills_map:
            if re.search(rf"\b{re.escape(skill)}\b", desc):
                if len(required) < 3:
                    required.append(skill)
                else:
                    preferred.append(skill)
        
        if "distributed systems" in desc or "distributed_systems" in desc:
            preferred.append("distributed_systems")

        _job_counter += 1
        job_id = f"JOB_{_job_counter:07d}"
        
        now_str = datetime.utcnow().isoformat() + "Z"
        job_record = {
            "job_id": job_id,
            "title": data.title,
            "status": JobStatus.ACTIVE,
            "required_skills": required if required else ["python"],
            "preferred_skills": preferred,
            "confidence_score": 0.90,
            "created_at": now_str,
            "updated_at": now_str,
            "candidate_count": 0
        }
        
        _jobs_db[job_id] = job_record
        return JobResponseData(**job_record)

    @staticmethod
    def list_jobs(
        status: Optional[str] = None,
        limit: int = 10,
        page_token: Optional[str] = None,
        created_after: Optional[str] = None
    ) -> List[JobListItem]:
        items = []
        for job in _jobs_db.values():
            if status and job["status"] != status:
                continue
            if created_after and job["created_at"] < created_after:
                continue
            items.append(JobListItem(
                job_id=job["job_id"],
                title=job["title"],
                status=job["status"],
                candidate_count=job.get("candidate_count", 0),
                created_at=job["created_at"]
            ))
        
        # Simple slicing for limit
        return items[:limit]

    @staticmethod
    def get_job(job_id: str) -> JobResponseData:
        if job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} was not found."
            )
        return JobResponseData(**_jobs_db[job_id])
