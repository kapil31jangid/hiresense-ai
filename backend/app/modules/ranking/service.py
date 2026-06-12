from typing import List, Dict, Optional
from datetime import datetime
import os
import csv

from app.common.schemas import (
    RankingCreate, RankingResponseData, RankingCandidateItem, RankingExportResponse,
    RankingStatus
)
from app.common.errors import HireSenseException
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db

_rankings_db: Dict[str, Dict] = {
    "rank_001": {
        "ranking_id": "rank_001",
        "job_id": "JOB_0000001",
        "status": RankingStatus.COMPLETED,
        "candidate_count": 1,
        "created_at": "2026-05-27T15:20:00Z",
        "candidates": [
            {
                "candidate_id": "CAND_0000001",
                "rank_position": 1,
                "fit_score": 0.91,
                "confidence_score": 0.87,
                "missing_required_skills": [],
                "top_match_reasons": [
                    "Strong semantic match for backend platform work",
                    "Direct evidence of FastAPI and PostgreSQL experience"
                ]
            }
        ]
    }
}
_ranking_counter = 1

class RankingService:
    @staticmethod
    def create_ranking(data: RankingCreate) -> RankingResponseData:
        global _ranking_counter
        # 1. Validate job_id
        if data.job_id not in _jobs_db:
            raise HireSenseException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job with ID {data.job_id} was not found."
            )
        
        job = _jobs_db[data.job_id]
        required_skills = [s.lower() for s in job.get("required_skills", [])]
        
        # 2. Validate candidate_ids
        candidates_scored = []
        for cand_id in data.candidate_ids:
            if cand_id not in _candidates_db:
                raise HireSenseException(
                    status_code=422,
                    code="CANDIDATE_PROFILE_INCOMPLETE",
                    message=f"Candidate profile incomplete or not found: {cand_id}"
                )
            
            cand = _candidates_db[cand_id]
            cand_skills = [s.lower() for s in cand.get("normalized_skills", [])]
            
            # Compute fit_score based on matching required skills
            missing_skills = [s for s in required_skills if s not in cand_skills]
            
            # Fit score calculations: base is matching required skills
            if required_skills:
                match_ratio = (len(required_skills) - len(missing_skills)) / len(required_skills)
            else:
                match_ratio = 1.0
                
            # Apply a penalty if there are missing required skills
            fit_score = match_ratio * 0.9 + 0.1  # simple scale
            if missing_skills:
                fit_score *= 0.8  # penalize gap
            
            fit_score = round(max(0.0, min(1.0, fit_score)), 2)
            confidence_score = cand.get("confidence_score", 0.85)
            
            reasons = [
                f"Direct evidence of {', '.join(required_skills[:2])} experience" if required_skills else "General profile match"
            ]
            if not missing_skills:
                reasons.append("All required job skills present in parsed profile.")
            else:
                reasons.append(f"Missing required skills: {', '.join(missing_skills)}")
                
            candidates_scored.append({
                "candidate_id": cand_id,
                "fit_score": fit_score,
                "confidence_score": confidence_score,
                "missing_required_skills": missing_skills,
                "top_match_reasons": reasons
            })
            
        # Sort candidates by fit_score descending
        candidates_scored.sort(key=lambda x: x["fit_score"], reverse=True)
        
        # Assign rank_position
        for idx, item in enumerate(candidates_scored):
            item["rank_position"] = idx + 1
            
        _ranking_counter += 1
        ranking_id = f"rank_{_ranking_counter:03d}"
        
        now_str = datetime.utcnow().isoformat() + "Z"
        ranking_record = {
            "ranking_id": ranking_id,
            "job_id": data.job_id,
            "status": RankingStatus.COMPLETED,
            "candidate_count": len(candidates_scored),
            "created_at": now_str,
            "candidates": candidates_scored
        }
        
        _rankings_db[ranking_id] = ranking_record
        return RankingResponseData(
            ranking_id=ranking_id,
            job_id=data.job_id,
            status=RankingStatus.COMPLETED,
            candidate_count=len(candidates_scored),
            created_at=now_str
        )

    @staticmethod
    def get_ranking_candidates(ranking_id: str) -> List[RankingCandidateItem]:
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )
        
        raw_candidates = _rankings_db[ranking_id]["candidates"]
        return [RankingCandidateItem(**c) for c in raw_candidates]

    @staticmethod
    def export_ranking_csv(ranking_id: str, request_id: str) -> RankingExportResponse:
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )
        
        ranking = _rankings_db[ranking_id]
        if ranking["status"] != RankingStatus.COMPLETED:
            raise HireSenseException(
                status_code=409,
                code="RANKING_NOT_READY_FOR_EXPORT",
                message="Ranking run is not completed or failed."
            )
        
        # Ensure export directory exists
        exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        file_name = f"{ranking_id}_shortlist.csv"
        file_path = os.path.join(exports_dir, file_name)
        
        # Write CSV using stored results - DO NOT RECOMPUTE
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["rank_position", "candidate_id", "fit_score", "confidence_score", "missing_required_skills"])
            for c in ranking["candidates"]:
                writer.writerow([
                    c["rank_position"],
                    c["candidate_id"],
                    c["fit_score"],
                    c["confidence_score"],
                    ",".join(c["missing_required_skills"])
                ])
                
        now_str = datetime.utcnow().isoformat() + "Z"
        download_url = f"/exports/{file_name}"
        
        return RankingExportResponse(
            request_id=request_id,
            ranking_id=ranking_id,
            file_name=file_name,
            content_type="text/csv",
            download_url=download_url,
            generated_at=now_str
        )
