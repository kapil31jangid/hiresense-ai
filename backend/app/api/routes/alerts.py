from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.common.schemas import AlertsResponse
from app.common.context import get_request_id
from app.api.auth import get_current_user
from app.modules.alerts.service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=AlertsResponse)
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH)"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    current_user=Depends(get_current_user)
):
    items = AlertService.list_alerts(
        status=status,
        alert_type=alert_type,
        severity=severity,
        job_id=job_id
    )
    return AlertsResponse(
        request_id=get_request_id(),
        items=items
    )
