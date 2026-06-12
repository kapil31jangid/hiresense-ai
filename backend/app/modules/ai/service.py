from app.common.schemas import AIExplanationRequest, AIExplanationResponse, AIGroundingData
from app.common.errors import HireSenseException
from app.modules.ranking.service import _rankings_db
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db

class AIService:
    @staticmethod
    def generate_explanation(data: AIExplanationRequest, request_id: str) -> AIExplanationResponse:
        # Validate ranking_id
        if data.ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {data.ranking_id} was not found."
            )
            
        ranking = _rankings_db[data.ranking_id]
        
        # Check if candidate is part of this ranking run
        cand_in_ranking = None
        for c in ranking["candidates"]:
            if c["candidate_id"] == data.candidate_id:
                cand_in_ranking = c
                break
                
        if not cand_in_ranking:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {data.candidate_id} was not found in ranking {data.ranking_id}."
            )
            
        job = _jobs_db[ranking["job_id"]]
        cand = _candidates_db[data.candidate_id]
        
        required_skills = job.get("required_skills", [])
        cand_skills = cand.get("normalized_skills", [])
        
        skills_used = [s for s in required_skills if s in cand_skills]
        missing_skills = [s for s in required_skills if s not in cand_skills]
        
        # Build explanation dynamically
        skills_str = ", ".join(skills_used) if skills_used else "none of the required skills"
        explanation = f"This candidate ranks highly because the resume provides direct evidence of {skills_str} experience, and the semantic match to the backend role is strong."
        
        if missing_skills:
            explanation += f" However, the following required skills are missing from the parsed profile: {', '.join(missing_skills)}."
        else:
            explanation += " No required skills are missing in the current profile."
            
        return AIExplanationResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            candidate_id=data.candidate_id,
            confidence_score=cand_in_ranking["confidence_score"],
            explanation=explanation,
            grounding=AIGroundingData(
                skills_used=skills_used,
                missing_required_skills=missing_skills
            )
        )
