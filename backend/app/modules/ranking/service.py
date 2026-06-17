from typing import List, Dict, Optional, Any
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
        "updated_at": "2026-05-27T15:20:00Z",
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
                ],
                "semantic_score": 0.94
            }
        ]
    }
}
_ranking_counter = 1


def _run_ranking_scoring(job_id: str, candidate_ids: List[str]) -> List[Dict[str, Any]]:
    # 1. Validate job_id
    if job_id not in _jobs_db:
        raise HireSenseException(
            status_code=404,
            code="JOB_NOT_FOUND",
            message=f"Job with ID {job_id} was not found."
        )
    job = _jobs_db[job_id]
    required_skills = [s.lower() for s in job.get("required_skills", [])]
    preferred_skills = [s.lower() for s in job.get("preferred_skills", [])]

    # 2. Fetch semantic search scores for the job (failures are handled gracefully)
    semantic_scores = {}
    try:
        from app.modules.semantic_search.service import SemanticSearchService
        from app.common.schemas import SemanticSearchRequest
        search_req = SemanticSearchRequest(job_id=job_id, top_k=1000)
        search_results = SemanticSearchService.search_candidates(search_req)
        for item in search_results:
            semantic_scores[item.candidate_id] = item.semantic_score
    except Exception:
        pass

    # 3. Score each candidate
    candidates_scored = []
    for cand_id in candidate_ids:
        if cand_id not in _candidates_db:
            raise HireSenseException(
                status_code=422,
                code="CANDIDATE_PROFILE_INCOMPLETE",
                message=f"Candidate profile incomplete or not found: {cand_id}"
            )
        
        cand = _candidates_db[cand_id]
        cand_skills = [s.lower() for s in cand.get("normalized_skills", [])]
        
        # Required skills match ratio
        missing_required = [s for s in required_skills if s not in cand_skills]
        if required_skills:
            required_match_ratio = (len(required_skills) - len(missing_required)) / len(required_skills)
        else:
            required_match_ratio = 1.0
            
        # Preferred skills match ratio
        missing_preferred = [s for s in preferred_skills if s not in cand_skills]
        if preferred_skills:
            preferred_match_ratio = (len(preferred_skills) - len(missing_preferred)) / len(preferred_skills)
        else:
            preferred_match_ratio = 1.0
            
        # Structured skill score (80% required, 20% preferred)
        if preferred_skills:
            structured_score = 0.8 * required_match_ratio + 0.2 * preferred_match_ratio
        else:
            structured_score = required_match_ratio
            
        # Semantic score (defaults to 0.0 if missing/failed)
        cand_sem_score = semantic_scores.get(cand_id, 0.0)
        
        # Fit score (40% semantic, 60% structured)
        fit_score = 0.4 * cand_sem_score + 0.6 * structured_score
        
        # Penalty for missing required skills: multiply by 0.8
        if missing_required:
            fit_score *= 0.8
            
        fit_score = round(max(0.0, min(1.0, fit_score)), 2)
        
        # Confidence score (starts with candidate's own parsed confidence)
        base_confidence = cand.get("confidence_score", 0.85)
        
        # Parsing status penalty
        if cand.get("parsing_status") == "PARTIAL":
            base_confidence -= 0.1
        elif cand.get("parsing_status") == "FAILED":
            base_confidence -= 0.3
            
        # Check experience evidence records
        from app.modules.candidate.service import CandidateService
        try:
            evidence_list = CandidateService.get_resume_evidence(cand_id)
        except Exception:
            evidence_list = []
            
        if not evidence_list:
            base_confidence -= 0.2
        else:
            # Check for matched required skills without evidence
            matched_required_skills = [s for s in required_skills if s in cand_skills]
            evidence_skills = [e.canonical_value.lower() for e in evidence_list if e.evidence_type == "SKILL"]
            unsupported_skills = [s for s in matched_required_skills if s not in evidence_skills]
            if unsupported_skills:
                base_confidence -= 0.05 * len(unsupported_skills)
                
        # Embedding status penalty
        from app.modules.semantic_search.service import _embeddings_db
        emb_record = _embeddings_db.get(f"emb_cand_{cand_id}")
        if not emb_record or emb_record.get("status") != "READY":
            base_confidence -= 0.15
            
        confidence_score = round(max(0.1, min(0.95, base_confidence)), 2)
        
        # Grounded match reasons/explanation factors
        reasons = []
        matched_required_skills = [s for s in required_skills if s in cand_skills]
        if matched_required_skills:
            reasons.append(f"Direct evidence of {', '.join(matched_required_skills[:3])} experience in resume.")
        else:
            if required_skills:
                reasons.append("No required skills found in candidate profile.")
            else:
                reasons.append("General profile match.")
                
        if cand_sem_score >= 0.85:
            reasons.append("Strong semantic alignment with role requirements.")
        elif cand_sem_score > 0.0:
            reasons.append("Moderate semantic match for backend platform work.")
            
        if missing_required:
            reasons.append(f"Missing required skills: {', '.join(missing_required)}")
            
        if not evidence_list:
            reasons.append("No parsed experience evidence found in profile.")
        elif len(evidence_list) < 3:
            reasons.append("Limited experience evidence parsed from resume.")
            
        if confidence_score < 0.65:
            reasons.append("Profile has low parsing confidence or incomplete fields.")
            
        candidates_scored.append({
            "candidate_id": cand_id,
            "fit_score": fit_score,
            "confidence_score": confidence_score,
            "missing_required_skills": missing_required,
            "top_match_reasons": reasons,
            "semantic_score": cand_sem_score
        })
        
    # Sort candidates stably: fit_score desc, confidence desc, candidate_id asc
    candidates_scored.sort(key=lambda x: (-x["fit_score"], -x["confidence_score"], x["candidate_id"]))
    
    # Assign rank positions
    for idx, item in enumerate(candidates_scored):
        item["rank_position"] = idx + 1
        
    return candidates_scored


class RankingService:
    @staticmethod
    def create_ranking(data: RankingCreate) -> RankingResponseData:
        global _ranking_counter
        
        candidates_scored = _run_ranking_scoring(data.job_id, data.candidate_ids)
        
        _ranking_counter += 1
        ranking_id = f"rank_{_ranking_counter:03d}"
        
        now_str = datetime.utcnow().isoformat() + "Z"
        ranking_record = {
            "ranking_id": ranking_id,
            "job_id": data.job_id,
            "status": RankingStatus.COMPLETED,
            "candidate_count": len(candidates_scored),
            "created_at": now_str,
            "updated_at": now_str,
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
    def get_ranking(ranking_id: str) -> RankingResponseData:
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )
        record = _rankings_db[ranking_id]
        return RankingResponseData(
            ranking_id=record["ranking_id"],
            job_id=record["job_id"],
            status=record["status"],
            candidate_count=record["candidate_count"],
            created_at=record["created_at"]
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
    def get_ranking_candidate_detail(ranking_id: str, candidate_id: str) -> RankingCandidateItem:
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )
        
        candidates = _rankings_db[ranking_id]["candidates"]
        for c in candidates:
            if c["candidate_id"] == candidate_id:
                return RankingCandidateItem(**c)
                
        raise HireSenseException(
            status_code=404,
            code="CANDIDATE_NOT_FOUND",
            message=f"Candidate with ID {candidate_id} was not found in ranking {ranking_id}."
        )

    @staticmethod
    def refresh_ranking(ranking_id: str) -> RankingResponseData:
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )
            
        record = _rankings_db[ranking_id]
        job_id = record["job_id"]
        candidate_ids = [c["candidate_id"] for c in record["candidates"]]
        
        candidates_scored = _run_ranking_scoring(job_id, candidate_ids)
        
        now_str = datetime.utcnow().isoformat() + "Z"
        record["status"] = RankingStatus.COMPLETED
        record["candidate_count"] = len(candidates_scored)
        record["updated_at"] = now_str
        record["candidates"] = candidates_scored
        
        return RankingResponseData(
            ranking_id=ranking_id,
            job_id=job_id,
            status=RankingStatus.COMPLETED,
            candidate_count=len(candidates_scored),
            created_at=record["created_at"]
        )

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
