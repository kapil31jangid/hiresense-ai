from datetime import datetime
from app.common.schemas import AnalyticsResponse, AnalyticsSummary, FreshnessStatus
from app.modules.job.service import _jobs_db
from app.modules.candidate.service import _candidates_db
from app.modules.ranking.service import _rankings_db
from app.modules.alerts.service import _alerts_db

class AnalyticsService:
    @staticmethod
    def get_dashboard_summary(request_id: str) -> AnalyticsResponse:
        # Dynamic computation from in-memory stores
        active_jobs = len(_jobs_db)
        parsed_candidates = len(_candidates_db)
        
        # Calculate active alerts count
        active_alerts = sum(1 for a in _alerts_db.values() if a["status"] == "ACTIVE")
        
        # Calculate average fit score
        fit_scores = []
        low_confidence_rankings = 0
        for ranking in _rankings_db.values():
            for c in ranking.get("candidates", []):
                fit_scores.append(c["fit_score"])
                if c["confidence_score"] < 0.88:
                    low_confidence_rankings += 1
                    
        avg_fit = round(sum(fit_scores) / len(fit_scores), 2) if fit_scores else 0.74
        
        now_str = datetime.utcnow().isoformat() + "Z"
        
        return AnalyticsResponse(
            request_id=request_id,
            analytics_last_updated_at=now_str,
            freshness_status=FreshnessStatus.FRESH,
            summary=AnalyticsSummary(
                active_jobs=active_jobs,
                parsed_candidates=parsed_candidates,
                active_alert_count=active_alerts,
                low_confidence_rankings=low_confidence_rankings,
                average_fit_score=avg_fit
            )
        )
