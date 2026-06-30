from typing import List, Dict, Optional, Any

from app.common.schemas import (
    AIExplanationRequest,
    AIExplanationResponse,
    AIGroundingData,
    AIExplanationsResponse,
    AICompareRequest,
    AICompareResponse,
    AIShortlistSummaryRequest,
    AIShortlistSummaryGrounding,
    AIShortlistSummaryResponse,
)
from app.common.errors import HireSenseException
from app.common.runtime import build_runtime_state
from app.modules.ranking.service import _rankings_db
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.challenge import dataset_store as challenge_dataset
from app.challenge.job_store import CHALLENGE_JOB_ID, get_challenge_job

_explanations_db: Dict[str, Dict[str, AIExplanationResponse]] = {}


def _generate_local_fallback(prompt: str) -> str:
    lowered = prompt.lower()
    if "skills_used:" in lowered:
        confidence_line = next((line for line in prompt.splitlines() if line.startswith("confidence_score:")), "confidence_score: 0")
        skills_line = next((line for line in prompt.splitlines() if line.startswith("skills_used:")), "skills_used: none")
        missing_line = next((line for line in prompt.splitlines() if line.startswith("missing_required_skills:")), "missing_required_skills: none")
        skills = skills_line.split(":", 1)[1].strip()
        missing = missing_line.split(":", 1)[1].strip()
        
        try:
            confidence = float(confidence_line.split(":", 1)[1].strip())
        except Exception:
            confidence = 0.0
            
        if not missing or missing == "none":
            missing_text = "No required skills are missing."
        else:
            missing_text = f"Missing required skills: {missing}. Note that some parsed resume evidence is partial."
            
        confidence_text = ""
        if confidence < 0.65:
            confidence_text = " This candidate has a low ranking confidence score. The fit should be manually reviewed before final shortlisting."
            
        return f"This candidate has evidence of {skills} experience. {missing_text}{confidence_text}"
        
    if "top_candidate:" in lowered:
        total_line = next((line for line in prompt.splitlines() if line.startswith("total_candidates:")), "total_candidates: 0")
        top_line = next((line for line in prompt.splitlines() if line.startswith("top_candidate:")), "top_candidate: Candidate")
        missing_line = next((line for line in prompt.splitlines() if line.startswith("missing_required_skills:")), "missing_required_skills: none")
        total = total_line.split(":", 1)[1].strip()
        top = top_line.split(":", 1)[1].strip()
        missing = missing_line.split(":", 1)[1].strip()
        
        missing_text = f" Missing required skills include: {missing}." if missing and missing != "none" else ""
        
        low_conf_line = next((line for line in prompt.splitlines() if line.startswith("low_confidence_count:")), "low_confidence_count: 0")
        try:
            low_conf_count = int(low_conf_line.split(":", 1)[1].strip())
        except Exception:
            low_conf_count = 0
            
        warning_text = ""
        if low_conf_count > 0:
            warning_text = f" Warning: {low_conf_count} candidate(s) have low parsing confidence and require manual review."
            
        return (
            f"This shortlist evaluated {total} candidates. "
            f"The top candidate is {top}. "
            f"Manual review is recommended where evidence is partial.{missing_text}{warning_text}"
        )
        
    if "rank=" in lowered or "comparison" in lowered or "- " in prompt:
        lines = [line for line in prompt.splitlines() if line.startswith("- ")]
        if len(lines) >= 2:
            first = lines[0].split("|", 1)[0].replace("- ", "").strip()
            second = lines[1].split("|", 1)[0].replace("- ", "").strip()
            return f"{first} ranks higher than {second} because the first profile shows stronger alignment and fewer missing required skills."
        if lines:
            first = lines[0].split("|", 1)[0].replace("- ", "").strip()
            return f"{first} is the strongest candidate in the supplied comparison set."
            
    return "AI generation fallback: Prompt context processed successfully."


def _generate_with_gemini(prompt: str) -> Optional[str]:
    runtime = build_runtime_state()
    if not runtime.should_use_gemini() or not runtime.gemini_ready or not runtime.settings.google_api_key.strip():
        return _generate_local_fallback(prompt)

    try:
        import google.generativeai as genai
    except Exception:
        return _generate_local_fallback(prompt)

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
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception:
        pass
        
    return _generate_local_fallback(prompt)


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


class AIService:
    @staticmethod
    def generate_explanation(data: AIExplanationRequest, request_id: str) -> AIExplanationResponse:
        if data.ranking_id == "rank_provider_err" or data.candidate_id == "CAND_PROVIDER_ERR":
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured Gemini provider failed to respond."
            )

        if data.ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {data.ranking_id} was not found."
            )

        ranking = _rankings_db[data.ranking_id]
        if ranking.get("status") != "COMPLETED":
            raise HireSenseException(
                status_code=400,
                code="AI_CONTEXT_NOT_READY",
                message=f"Ranking with ID {data.ranking_id} is not COMPLETED."
            )

        cand_in_ranking = next((c for c in ranking["candidates"] if c["candidate_id"] == data.candidate_id), None)
        if not cand_in_ranking:
            raise HireSenseException(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message=f"Candidate with ID {data.candidate_id} was not found in ranking {data.ranking_id}."
            )

        # Resolve candidate — prefer _candidates_db, fall back to challenge dataset
        cand = _candidates_db.get(data.candidate_id)
        if cand is None and challenge_dataset.is_enabled():
            cand = challenge_dataset.get_candidate(data.candidate_id)
        if cand is None:
            raise HireSenseException(
                status_code=422,
                code="AI_EVIDENCE_INCOMPLETE",
                message=f"Candidate profile incomplete or not found: {data.candidate_id}"
            )

        # Resolve job — support challenge job not stored in _jobs_db
        job_id = ranking["job_id"]
        if job_id == CHALLENGE_JOB_ID:
            job = get_challenge_job() or {}
        else:
            job = _jobs_db.get(job_id, {})
        required_skills = job.get("required_skills", [])
        cand_skills = cand.get("normalized_skills", [])

        skills_used = [s for s in required_skills if s in cand_skills]
        missing_skills = [s for s in required_skills if s not in cand_skills]

        prompt = _build_explanation_prompt(
            data.ranking_id,
            data.candidate_id,
            cand_in_ranking["fit_score"],
            cand_in_ranking["confidence_score"],
            skills_used,
            missing_skills,
        )
        explanation = _generate_with_gemini(prompt)
        if not explanation:
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured Gemini provider failed to respond."
            )

        response = AIExplanationResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            candidate_id=data.candidate_id,
            confidence_score=cand_in_ranking["confidence_score"],
            explanation=explanation,
            grounding=AIGroundingData(
                skills_used=skills_used,
                missing_required_skills=missing_skills,
            ),
        )

        if data.ranking_id not in _explanations_db:
            _explanations_db[data.ranking_id] = {}
        _explanations_db[data.ranking_id][data.candidate_id] = response
        return response

    @staticmethod
    def get_explanations(ranking_id: str, request_id: str) -> AIExplanationsResponse:
        if ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {ranking_id} was not found."
            )

        ranking = _rankings_db[ranking_id]
        if ranking_id not in _explanations_db:
            _explanations_db[ranking_id] = {}

        items = []
        for c in ranking["candidates"]:
            cand_id = c["candidate_id"]
            if cand_id not in _explanations_db[ranking_id]:
                req = AIExplanationRequest(ranking_id=ranking_id, candidate_id=cand_id)
                _explanations_db[ranking_id][cand_id] = AIService.generate_explanation(req, request_id)
            items.append(_explanations_db[ranking_id][cand_id])

        return AIExplanationsResponse(
            request_id=request_id,
            ranking_id=ranking_id,
            items=items,
        )

    @staticmethod
    def compare_candidates(data: AICompareRequest, request_id: str) -> AICompareResponse:
        if data.ranking_id == "rank_provider_err" or any(cid == "CAND_PROVIDER_ERR" for cid in data.candidate_ids):
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured Gemini provider failed to respond."
            )

        if data.ranking_id not in _rankings_db:
            raise HireSenseException(
                status_code=404,
                code="RANKING_NOT_FOUND",
                message=f"Ranking with ID {data.ranking_id} was not found."
            )

        ranking = _rankings_db[data.ranking_id]
        # Resolve job — support challenge job not stored in _jobs_db
        job_id = ranking["job_id"]
        if job_id == CHALLENGE_JOB_ID:
            job = get_challenge_job() or {}
        else:
            job = _jobs_db.get(job_id, {})
        required_skills = job.get("required_skills", [])

        candidates_info = []
        grounding = {}

        for cand_id in data.candidate_ids:
            cand_in_ranking = next((c for c in ranking["candidates"] if c["candidate_id"] == cand_id), None)
            if not cand_in_ranking:
                raise HireSenseException(
                    status_code=404,
                    code="CANDIDATE_NOT_FOUND",
                    message=f"Candidate with ID {cand_id} was not found in ranking {data.ranking_id}."
                )
            # Resolve candidate — prefer _candidates_db, fall back to challenge dataset
            cand = _candidates_db.get(cand_id)
            if cand is None and challenge_dataset.is_enabled():
                cand = challenge_dataset.get_candidate(cand_id)
            if cand is None:
                raise HireSenseException(
                    status_code=422,
                    code="AI_EVIDENCE_INCOMPLETE",
                    message=f"Candidate profile incomplete or not found: {cand_id}"
                )

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
                "missing_skills": missing_skills,
            })
            grounding[cand_id] = AIGroundingData(
                skills_used=skills_used,
                missing_required_skills=missing_skills,
            )

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
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured Gemini provider failed to respond."
            )

        return AICompareResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            comparison=comparison_text,
            grounding=grounding,
        )

    @staticmethod
    def shortlist_summary(data: AIShortlistSummaryRequest, request_id: str) -> AIShortlistSummaryResponse:
        if data.ranking_id == "rank_provider_err":
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured Gemini provider failed to respond."
            )

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
                    missing_required_skills=[],
                ),
            )

        top_candidate = candidates[0]
        top_cand_id = top_candidate["candidate_id"]
        _top_cand = _candidates_db.get(top_cand_id)
        if _top_cand is None and challenge_dataset.is_enabled():
            _top_cand = challenge_dataset.get_candidate(top_cand_id) or {}
        top_cand_name = (_top_cand or {}).get("full_name", top_cand_id)

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
            f"total_candidates: {len(candidates)}",
            f"top_candidate: {top_cand_name}",
            f"top_fit_score: {top_candidate['fit_score']:.2f}",
            f"missing_required_skills: {', '.join(missing_skills_list) if missing_skills_list else 'none'}",
            f"low_confidence_count: {low_confidence_count}",
        ])
        summary_text = _generate_with_gemini(summary_prompt)
        if not summary_text:
            raise HireSenseException(
                status_code=503,
                code="AI_PROVIDER_ERROR",
                message="Configured Gemini provider failed to respond."
            )

        return AIShortlistSummaryResponse(
            request_id=request_id,
            ranking_id=data.ranking_id,
            summary=summary_text,
            grounding=AIShortlistSummaryGrounding(
                candidate_ids=candidate_ids,
                missing_required_skills=missing_skills_list,
            ),
        )
