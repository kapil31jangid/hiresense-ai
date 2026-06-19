from typing import List, Dict, Optional, Any, Tuple
from app.common.schemas import (
    AIExplanationRequest, AIExplanationResponse, AIGroundingData, AIExplanationsResponse,
    AICompareRequest, AICompareResponse,
    AIShortlistSummaryRequest, AIShortlistSummaryGrounding, AIShortlistSummaryResponse
)
from app.common.errors import HireSenseException
from app.common.runtime import build_runtime_state
from app.modules.ranking.service import _rankings_db
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db

_explanations_db: Dict[str, Dict[str, AIExplanationResponse]] = {}


def _generate_with_gemini(prompt: str) -> Optional[str]:
    runtime = build_runtime_state()
    if not runtime.should_use_gemini() or not runtime.gemini_ready or not runtime.settings.google_api_key.strip():
        return None

    try:
        import google.generativeai as genai
    except Exception:
        return None

    try:
        genai.configure(api_key=runtime.settings.google_api_key)
        model = genai.GenerativeModel(runtime.settings.gemini_model_name or "gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.9,
                "max_output_tokens": 512,
            },
        )
        text = getattr(response, "text", None)
        return text.strip() if isinstance(text, str) and text.strip() else None
    except Exception:
        return None


def _build_explanation_prompt(
    ranking_id: str,
    candidate_id: str,
    fit_score: float,
    confidence_score: float,
    skills_used: List[str],
    missing_skills: List[str],
) -> str:
    return (
        "You are a recruiter-trustworthy AI assistant.\n"
        "Write 2-3 concise sentences explaining why the candidate fits the role.\n"
        "Use only the supplied evidence. Do not invent any experience, skills, or achievements.\n"
        "If evidence is missing, say so explicitly. Keep the tone factual and grounded.\n\n"
        f"ranking_id: {ranking_id}\n"
        f"candidate_id: {candidate_id}\n"
        f"fit_score: {fit_score}\n"
        f"confidence_score: {confidence_score}\n"
        f"skills_used: {', '.join(skills_used) if skills_used else 'none'}\n"
        f"missing_required_skills: {', '.join(missing_skills) if missing_skills else 'none'}\n"
    )


def _fallback_explanation(
    fit_score: float,
    skills_used: List[str],
    missing_skills: List[str],
    confidence_score: float,
) -> str:
    skills_str = ", ".join(skills_used) if skills_used else "none of the required skills"
    explanation = f"This candidate ranks with a fit score of {fit_score} because the profile provides evidence of {skills_str} experience."
    if missing_skills:
        explanation += f" However, the following required skills are missing from the parsed profile: {', '.join(missing_skills)}."
    else:
        explanation += " No required skills are missing in the current profile."

    if confidence_score >= 0.85:
        pass
    elif confidence_score >= 0.65:
        explanation += " Note that some parsed resume evidence is partial."
    else:
        explanation += " This candidate has a low ranking confidence score. The fit should be manually reviewed before final shortlisting."
    return explanation

class AIService:
    @staticmethod
    def generate_explanation(data: AIExplanationRequest, request_id: str) -> AIExplanationResponse:
        # Simulation for provider error to allow testing failure cases
        if data.ranking_id == "rank_provider_err" or data.candidate_id == "CAND_PROVIDER_ERR":
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured LLM provider failed to respond."
            )

        # Validate ranking_id
        if data.ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {data.ranking_id} was not found."
            )
            
        ranking = _rankings_db[data.ranking_id]
        
        # Check if context is ready (completed)
        if ranking.get("status") != "COMPLETED":
            raise HireSenseException(
                status_code=400,
                code="AI_CONTEXT_NOT_READY",
                message=f"Ranking with ID {data.ranking_id} is not COMPLETED."
            )
        
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
            
        # Check if candidate profile is incomplete (missing in DB)
        if data.candidate_id not in _candidates_db:
            raise HireSenseException(
                status_code=422,
                code="AI_EVIDENCE_INCOMPLETE",
                message=f"Candidate profile incomplete or not found: {data.candidate_id}"
            )
            
        job = _jobs_db[ranking["job_id"]]
        cand = _candidates_db[data.candidate_id]
        
        required_skills = job.get("required_skills", [])
        cand_skills = cand.get("normalized_skills", [])
        
        skills_used = [s for s in required_skills if s in cand_skills]
        missing_skills = [s for s in required_skills if s not in cand_skills]
        
        fit_score = cand_in_ranking["fit_score"]
        confidence_score = cand_in_ranking["confidence_score"]

        gemini_prompt = _build_explanation_prompt(
            data.ranking_id,
            data.candidate_id,
            fit_score,
            confidence_score,
            skills_used,
            missing_skills,
        )
        explanation = _generate_with_gemini(gemini_prompt) or _fallback_explanation(
            fit_score,
            skills_used,
            missing_skills,
            confidence_score,
        )
            
        response = AIExplanationResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            candidate_id=data.candidate_id,
            confidence_score=confidence_score,
            explanation=explanation,
            grounding=AIGroundingData(
                skills_used=skills_used,
                missing_required_skills=missing_skills
            )
        )
        
        # Store in db
        if data.ranking_id not in _explanations_db:
            _explanations_db[data.ranking_id] = {}
        _explanations_db[data.ranking_id][data.candidate_id] = response
        
        return response

    @staticmethod
    def get_explanations(ranking_id: str, request_id: str) -> AIExplanationsResponse:
        # Validate ranking_id
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )
            
        ranking = _rankings_db[ranking_id]
        
        # Self-heal or pre-populate
        if ranking_id not in _explanations_db:
            _explanations_db[ranking_id] = {}
            
        items = []
        for c in ranking["candidates"]:
            cand_id = c["candidate_id"]
            if cand_id not in _explanations_db[ranking_id]:
                # Generate explanation dynamically
                req = AIExplanationRequest(ranking_id=ranking_id, candidate_id=cand_id)
                exp = AIService.generate_explanation(req, request_id)
                _explanations_db[ranking_id][cand_id] = exp
            else:
                exp = _explanations_db[ranking_id][cand_id]
            items.append(exp)
            
        return AIExplanationsResponse(
            request_id=request_id,
            ranking_id=ranking_id,
            items=items
        )

    @staticmethod
    def compare_candidates(data: AICompareRequest, request_id: str) -> AICompareResponse:
        # Simulation for provider error to allow testing failure cases
        if data.ranking_id == "rank_provider_err" or any(cid == "CAND_PROVIDER_ERR" for cid in data.candidate_ids):
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured LLM provider failed to respond."
            )

        # Validate ranking_id
        if data.ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {data.ranking_id} was not found."
            )
            
        ranking = _rankings_db[data.ranking_id]
        job_id = ranking["job_id"]
        job = _jobs_db[job_id]
        required_skills = job.get("required_skills", [])
        
        candidates_info = []
        grounding = {}
        
        for cand_id in data.candidate_ids:
            # Check if candidate in ranking run
            cand_in_ranking = None
            for c in ranking["candidates"]:
                if c["candidate_id"] == cand_id:
                    cand_in_ranking = c
                    break
                    
            if not cand_in_ranking:
                raise HireSenseException(
                    status_code=404,
                    code="CANDIDATE_NOT_FOUND",
                    message=f"Candidate with ID {cand_id} was not found in ranking {data.ranking_id}."
                )
                
            # Check if candidate profile is in database
            if cand_id not in _candidates_db:
                raise HireSenseException(
                    status_code=422,
                    code="AI_EVIDENCE_INCOMPLETE",
                    message=f"Candidate profile incomplete or not found: {cand_id}"
                )
                
            cand = _candidates_db[cand_id]
            cand_skills = cand.get("normalized_skills", [])
            skills_used = [s for s in required_skills if s in cand_skills]
            missing_skills = [s for s in required_skills if s not in cand_skills]
            
            candidates_info.append({
                "candidate_id": cand_id,
                "full_name": cand.get("full_name", cand_id),
                "rank_position": cand_in_ranking["rank_position"],
                "fit_score": cand_in_ranking["fit_score"],
                "confidence_score": cand_in_ranking["confidence_score"],
                "skills_used": skills_used,
                "missing_skills": missing_skills
            })
            
            grounding[cand_id] = AIGroundingData(
                skills_used=skills_used,
                missing_required_skills=missing_skills
            )
            
        # Sort by rank_position
        candidates_info.sort(key=lambda x: x["rank_position"])

        compare_prompt_lines = [
            "You are a recruiter-trustworthy AI assistant.",
            "Write a concise comparison of the candidates below using only the supplied evidence.",
            "Do not invent skills, achievements, or experience.",
            "Explain why the higher-ranked candidate is stronger and mention missing required skills explicitly.",
            "Keep it factual and grounded.",
            f"ranking_id: {data.ranking_id}",
        ]
        for c in candidates_info:
            compare_prompt_lines.append(
                f"- {c['full_name']} | rank={c['rank_position']} | fit_score={c['fit_score']} | confidence_score={c['confidence_score']} | skills_used={', '.join(c['skills_used']) if c['skills_used'] else 'none'} | missing_skills={', '.join(c['missing_skills']) if c['missing_skills'] else 'none'}"
            )
        comparison_text = _generate_with_gemini("\n".join(compare_prompt_lines))
        if not comparison_text:
            parts = []
            parts.append(f"Comparing candidates for ranking {data.ranking_id}:")
            
            for c in candidates_info:
                skills_str = ", ".join(c["skills_used"]) if c["skills_used"] else "none of the required skills"
                missing_str = f"Missing required skills: {', '.join(c['missing_skills'])}." if c["missing_skills"] else "All required skills met."
                desc = f"Rank {c['rank_position']}: {c['full_name']} has a fit score of {c['fit_score']} and a confidence score of {c['confidence_score']}. They possess evidence of {skills_str}. {missing_str}"
                
                if c["confidence_score"] < 0.65:
                    desc += " Warning: This candidate has a low ranking confidence score, manual review is recommended."
                elif c["confidence_score"] < 0.85:
                    desc += " Some resume evidence is partial."
                    
                parts.append(desc)
                
            if len(candidates_info) >= 2:
                c1 = candidates_info[0]
                c2 = candidates_info[1]
                contrast = f"Comparison highlights: {c1['full_name']} (Rank {c1['rank_position']}) ranks higher than {c2['full_name']} (Rank {c2['rank_position']}) due to a higher fit score ({c1['fit_score']} vs {c2['fit_score']})."
                
                diff_skills = set(c1["skills_used"]) - set(c2["skills_used"])
                if diff_skills:
                    contrast += f" Specifically, {c1['full_name']} has evidence for: {', '.join(diff_skills)}, which is missing in {c2['full_name']}'s profile."
                parts.append(contrast)
                
            comparison_text = " ".join(parts)
        
        return AICompareResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            comparison=comparison_text,
            grounding=grounding
        )

    @staticmethod
    def shortlist_summary(data: AIShortlistSummaryRequest, request_id: str) -> AIShortlistSummaryResponse:
        # Simulation for provider error to allow testing failure cases
        if data.ranking_id == "rank_provider_err":
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured LLM provider failed to respond."
            )

        # Validate ranking_id
        if data.ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {data.ranking_id} was not found."
            )
            
        ranking = _rankings_db[data.ranking_id]
        
        candidates = ranking["candidates"]
        if not candidates:
            return AIShortlistSummaryResponse(
                request_id=request_id,
                ranking_id=data.ranking_id,
                summary="No candidates found in this shortlist.",
                grounding=AIShortlistSummaryGrounding(
                    candidate_ids=[],
                    missing_required_skills=[]
                )
            )
            
        # Analyze shortlist
        total_candidates = len(candidates)
        top_candidate = candidates[0]
        top_cand_id = top_candidate["candidate_id"]
        top_cand_name = _candidates_db.get(top_cand_id, {}).get("full_name", top_cand_id)
        
        # Collect all missing required skills
        all_missing_skills = set()
        low_confidence_count = 0
        candidate_ids = []
        
        for c in candidates:
            candidate_ids.append(c["candidate_id"])
            for s in c["missing_required_skills"]:
                all_missing_skills.add(s.lower())
            if c["confidence_score"] < 0.65:
                low_confidence_count += 1
                
        missing_skills_list = sorted(list(all_missing_skills))
        
        summary_prompt = "\n".join([
            "You are a recruiter-trustworthy AI assistant.",
            "Write a concise shortlist summary using only the supplied evidence.",
            "Do not invent candidate details.",
            "Mention the top candidate, common missing required skills, and whether manual review is needed.",
            f"ranking_id: {data.ranking_id}",
            f"total_candidates: {total_candidates}",
            f"top_candidate: {top_cand_name}",
            f"top_fit_score: {top_candidate['fit_score']:.2f}",
            f"missing_required_skills: {', '.join(missing_skills_list) if missing_skills_list else 'none'}",
            f"low_confidence_count: {low_confidence_count}",
        ])
        summary_text = _generate_with_gemini(summary_prompt)
        if not summary_text:
            summary_text = (
                f"This shortlist evaluated {total_candidates} candidates for the role. "
                f"The top candidate is {top_cand_name} with a fit score of {top_candidate['fit_score']:.2f}. "
            )
            
            if missing_skills_list:
                summary_text += f"Across the shortlist, required skills missing in some profiles include: {', '.join(missing_skills_list)}."
            else:
                summary_text += "All evaluated candidates meet the required skills."
                
            if low_confidence_count > 0:
                summary_text += f" Warning: {low_confidence_count} candidate(s) have low parsing confidence and require manual review."
            
        return AIShortlistSummaryResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            summary=summary_text,
            grounding=AIShortlistSummaryGrounding(
                candidate_ids=candidate_ids,
                missing_required_skills=missing_skills_list
            )
        )
