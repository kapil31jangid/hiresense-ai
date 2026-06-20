from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.common.errors import HireSenseException
from app.common.schemas import (
    AnalyticsResponse,
    AnalyticsSummary,
    CandidateFunnelResponse,
    CandidateFunnelSummary,
    FreshnessStatus,
    HiringInsightItem,
    HiringInsightsResponse,
    RankingQualityResponse,
    RankingQualitySummary,
    SkillDistributionItem,
    SkillDistributionResponse,
)
from app.modules.alerts.service import _alerts_db
from app.modules.candidate.service import _candidates_db
from app.modules.job.service import _jobs_db
from app.modules.ranking.service import _rankings_db
from app.challenge import dataset_store as challenge_dataset
from app.common.runtime import load_settings

LOW_CONFIDENCE_THRESHOLD = 0.88
SHORTLIST_FIT_THRESHOLD = 0.80

_analytics_last_updated_at: Optional[str] = "2026-05-27T15:30:00Z"
_freshness_status: FreshnessStatus = FreshnessStatus.FRESH
_analytics_aggregates: Optional[Dict[str, Any]] = None


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _round_score(value: float) -> float:
    return round(value, 2)


def _iter_ranking_candidates() -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for ranking in _rankings_db.values():
        candidates.extend(ranking.get("candidates", []))
    return candidates


def _challenge_candidate_count() -> int:
    status = challenge_dataset.index_status()
    return int(status.get("candidate_count") or 0) if status.get("enabled") else 0


def _official_submission_rows() -> List[Dict[str, Any]]:
    if not challenge_dataset.is_enabled():
        return []
    settings = load_settings()
    path = Path(settings.challenge_submission_output_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[4] / path
    if not path.exists():
        return []
    try:
        import csv

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def _build_dashboard_summary(ranked_candidates: List[Dict[str, Any]]) -> AnalyticsSummary:
    fit_scores = [candidate.get("fit_score", 0.0) for candidate in ranked_candidates]
    low_confidence_count = sum(
        1
        for candidate in ranked_candidates
        if candidate.get("confidence_score", 0.0) < LOW_CONFIDENCE_THRESHOLD
    )
    active_jobs = sum(1 for job in _jobs_db.values() if _enum_value(job.get("status")) == "ACTIVE")
    challenge_count = _challenge_candidate_count()
    parsed_candidates = challenge_count or sum(
        1
        for candidate in _candidates_db.values()
        if candidate.get("parsing_status") in {"COMPLETED", "PARTIAL"}
    )
    active_alert_count = sum(
        1 for alert in _alerts_db.values() if _enum_value(alert.get("status")) == "ACTIVE"
    )

    return AnalyticsSummary(
        active_jobs=active_jobs,
        parsed_candidates=parsed_candidates,
        active_alert_count=active_alert_count,
        low_confidence_rankings=low_confidence_count,
        average_fit_score=_round_score(sum(fit_scores) / len(fit_scores)) if fit_scores else 0.0,
    )


def _build_ranking_quality(ranked_candidates: List[Dict[str, Any]]) -> RankingQualitySummary:
    official_rows = _official_submission_rows()
    if official_rows and not ranked_candidates:
        scores = [float(row.get("score") or 0.0) for row in official_rows]
        return RankingQualitySummary(
            ranking_count=1,
            ranked_candidate_count=len(official_rows),
            average_fit_score=_round_score(sum(scores) / len(scores)) if scores else 0.0,
            average_confidence_score=0.0,
            low_confidence_count=0,
        )

    fit_scores = [candidate.get("fit_score", 0.0) for candidate in ranked_candidates]
    confidence_scores = [candidate.get("confidence_score", 0.0) for candidate in ranked_candidates]
    low_confidence_count = sum(
        1 for score in confidence_scores if score < LOW_CONFIDENCE_THRESHOLD
    )

    return RankingQualitySummary(
        ranking_count=len(_rankings_db),
        ranked_candidate_count=len(ranked_candidates),
        average_fit_score=_round_score(sum(fit_scores) / len(fit_scores)) if fit_scores else 0.0,
        average_confidence_score=(
            _round_score(sum(confidence_scores) / len(confidence_scores)) if confidence_scores else 0.0
        ),
        low_confidence_count=low_confidence_count,
    )


def _build_skill_distribution() -> List[SkillDistributionItem]:
    job_skill_counts: Counter[str] = Counter()
    candidate_skill_counts: Counter[str] = Counter()

    for job in _jobs_db.values():
        job_skills = set(job.get("required_skills", [])) | set(job.get("preferred_skills", []))
        job_skill_counts.update(job_skills)

    for candidate in _candidates_db.values():
        candidate_skill_counts.update(set(candidate.get("normalized_skills", [])))

    skill_names = sorted(set(job_skill_counts) | set(candidate_skill_counts))
    return [
        SkillDistributionItem(
            skill_name=skill_name,
            job_count=job_skill_counts[skill_name],
            candidate_count=candidate_skill_counts[skill_name],
        )
        for skill_name in skill_names
    ]


def _build_candidate_funnel(ranked_candidates: List[Dict[str, Any]]) -> CandidateFunnelSummary:
    challenge_count = _challenge_candidate_count()
    official_rows = _official_submission_rows()
    ranked_candidate_ids: Set[str] = {
        candidate["candidate_id"]
        for candidate in ranked_candidates
        if candidate.get("candidate_id")
    }
    shortlisted_candidate_ids: Set[str] = {
        candidate["candidate_id"]
        for candidate in ranked_candidates
        if candidate.get("candidate_id") and candidate.get("fit_score", 0.0) >= SHORTLIST_FIT_THRESHOLD
    }
    parsed_candidates = challenge_count or sum(
        1
        for candidate in _candidates_db.values()
        if candidate.get("parsing_status") in {"COMPLETED", "PARTIAL"}
    )

    return CandidateFunnelSummary(
        uploaded_candidates=challenge_count or len(_candidates_db),
        parsed_candidates=parsed_candidates,
        ranked_candidates=len(official_rows) if official_rows else len(ranked_candidate_ids),
        shortlisted_candidates=len(official_rows) if official_rows else len(shortlisted_candidate_ids),
    )


def _build_hiring_insights(
    dashboard: AnalyticsSummary,
    ranking_quality: RankingQualitySummary,
    skill_distribution: List[SkillDistributionItem],
    candidate_funnel: CandidateFunnelSummary,
) -> List[HiringInsightItem]:
    insights: List[HiringInsightItem] = [
        HiringInsightItem(
            insight_type="RANKING_QUALITY",
            title="Ranking confidence",
            message=(
                f"{ranking_quality.low_confidence_count} ranked candidates are below the "
                f"{LOW_CONFIDENCE_THRESHOLD:.2f} confidence threshold."
            ),
            metric_value=float(ranking_quality.low_confidence_count),
        ),
        HiringInsightItem(
            insight_type="PIPELINE_FRESHNESS",
            title="Analytics freshness",
            message=f"Analytics freshness status is {_enum_value(_freshness_status)}.",
        ),
    ]

    if skill_distribution:
        top_skill = max(
            skill_distribution,
            key=lambda item: (item.candidate_count + item.job_count, item.skill_name),
        )
        insights.append(
            HiringInsightItem(
                insight_type="SKILL_DISTRIBUTION",
                title="Most visible skill",
                message=(
                    f"{top_skill.skill_name} appears across "
                    f"{top_skill.job_count} jobs and {top_skill.candidate_count} candidates."
                ),
                metric_value=float(top_skill.job_count + top_skill.candidate_count),
            )
        )

    if candidate_funnel.uploaded_candidates:
        ranked_ratio = candidate_funnel.ranked_candidates / candidate_funnel.uploaded_candidates
        insights.append(
            HiringInsightItem(
                insight_type="CANDIDATE_FUNNEL",
                title="Candidate ranking coverage",
                message=(
                    f"{candidate_funnel.ranked_candidates} of "
                    f"{candidate_funnel.uploaded_candidates} candidates appear in stored rankings."
                ),
                metric_value=_round_score(ranked_ratio),
            )
        )

    insights.append(
        HiringInsightItem(
            insight_type="DASHBOARD_SUMMARY",
            title="Open hiring activity",
            message=(
                f"{dashboard.active_jobs} active jobs and {dashboard.active_alert_count} "
                "active alerts are represented in the analytics snapshot."
            ),
            metric_value=float(dashboard.active_jobs),
        )
    )
    return insights


def _build_aggregates() -> Dict[str, Any]:
    ranked_candidates = _iter_ranking_candidates()
    dashboard = _build_dashboard_summary(ranked_candidates)
    ranking_quality = _build_ranking_quality(ranked_candidates)
    skill_distribution = _build_skill_distribution()
    candidate_funnel = _build_candidate_funnel(ranked_candidates)
    hiring_insights = _build_hiring_insights(
        dashboard,
        ranking_quality,
        skill_distribution,
        candidate_funnel,
    )

    return {
        "dashboard": dashboard,
        "ranking_quality": ranking_quality,
        "skill_distribution": skill_distribution,
        "candidate_funnel": candidate_funnel,
        "hiring_insights": hiring_insights,
    }


def _ensure_available() -> Dict[str, Any]:
    if challenge_dataset.is_enabled():
        now_str = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        AnalyticsService.refresh_aggregates(now_str, FreshnessStatus.FRESH)
    if not _analytics_last_updated_at or _analytics_aggregates is None:
        raise HireSenseException(
            status_code=503,
            code="ANALYTICS_NOT_READY",
            message="Analytics aggregates are not available yet.",
            details={"freshness_status": _enum_value(_freshness_status)},
        )
    return _analytics_aggregates

class AnalyticsService:
    @staticmethod
    def refresh_aggregates(last_updated_at: str, status: FreshnessStatus) -> None:
        global _analytics_last_updated_at, _freshness_status, _analytics_aggregates
        _analytics_last_updated_at = last_updated_at
        _freshness_status = status
        
        from app.modules.alerts.service import AlertService
        try:
            AlertService.run_evaluation_sweep()
        except Exception:
            pass
            
        _analytics_aggregates = _build_aggregates()

    @staticmethod
    def update_freshness(last_updated_at: str, status: FreshnessStatus) -> None:
        AnalyticsService.refresh_aggregates(last_updated_at, status)

    @staticmethod
    def get_dashboard_summary(request_id: str) -> AnalyticsResponse:
        aggregates = _ensure_available()
        return AnalyticsResponse(
            request_id=request_id,
            analytics_last_updated_at=_analytics_last_updated_at,
            freshness_status=_freshness_status,
            summary=aggregates["dashboard"],
        )

    @staticmethod
    def get_ranking_quality(request_id: str) -> RankingQualityResponse:
        aggregates = _ensure_available()
        return RankingQualityResponse(
            request_id=request_id,
            analytics_last_updated_at=_analytics_last_updated_at,
            freshness_status=_freshness_status,
            summary=aggregates["ranking_quality"],
        )

    @staticmethod
    def get_skill_distribution(request_id: str) -> SkillDistributionResponse:
        aggregates = _ensure_available()
        return SkillDistributionResponse(
            request_id=request_id,
            analytics_last_updated_at=_analytics_last_updated_at,
            freshness_status=_freshness_status,
            items=aggregates["skill_distribution"],
        )

    @staticmethod
    def get_candidate_funnel(request_id: str) -> CandidateFunnelResponse:
        aggregates = _ensure_available()
        return CandidateFunnelResponse(
            request_id=request_id,
            analytics_last_updated_at=_analytics_last_updated_at,
            freshness_status=_freshness_status,
            summary=aggregates["candidate_funnel"],
        )

    @staticmethod
    def get_hiring_insights(request_id: str) -> HiringInsightsResponse:
        aggregates = _ensure_available()
        return HiringInsightsResponse(
            request_id=request_id,
            analytics_last_updated_at=_analytics_last_updated_at,
            freshness_status=_freshness_status,
            items=aggregates["hiring_insights"],
        )


_analytics_aggregates = _build_aggregates()
