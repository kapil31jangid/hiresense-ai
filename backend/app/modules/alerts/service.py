from typing import List, Optional, Dict
from app.common.schemas import AlertItem, AlertStatus, AlertSeverity

# In-memory DB of alerts
_alerts_db: Dict[str, Dict] = {
    "alert_rank_001": {
        "alert_id": "alert_rank_001",
        "alert_type": "LOW_CONFIDENCE_RANKING",
        "status": AlertStatus.ACTIVE,
        "severity": AlertSeverity.HIGH,
        "title": "Ranking confidence is low for Senior Backend Engineer",
        "message": "Required skill evidence is incomplete for top candidates.",
        "created_at": "2026-05-27T15:25:00Z",
        "job_id": "JOB_0000001"
    }
}

class AlertService:
    @staticmethod
    def list_alerts(
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> List[AlertItem]:
        items = []
        for alert in _alerts_db.values():
            if status and alert["status"] != status:
                continue
            if alert_type and alert["alert_type"] != alert_type:
                continue
            if severity and alert["severity"] != severity:
                continue
            if job_id and alert.get("job_id") != job_id:
                continue
                
            items.append(AlertItem(
                alert_id=alert["alert_id"],
                alert_type=alert["alert_type"],
                status=alert["status"],
                severity=alert["severity"],
                title=alert["title"],
                message=alert["message"],
                created_at=alert["created_at"],
                job_id=alert.get("job_id")
            ))
        return items
