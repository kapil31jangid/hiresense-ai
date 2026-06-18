from fastapi import APIRouter, Depends, Query, status
from typing import Optional, Dict
from pydantic import BaseModel

from app.common.schemas import AlertsResponse, AlertItem
from app.common.context import get_request_id
from app.api.auth import get_current_user, UserContext
from app.modules.alerts.service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])

class AlertsSummaryResponse(BaseModel):
    request_id: str
    active_count: int
    acknowledged_count: int
    resolved_count: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]

class AlertResponse(BaseModel):
    request_id: str
    alert: AlertItem

class ResolveAlertRequest(BaseModel):
    resolution_note: Optional[str] = None

@router.get("", response_model=AlertsResponse)
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH)"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    current_user: UserContext = Depends(get_current_user)
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

@router.get("/summary", response_model=AlertsSummaryResponse)
def get_alerts_summary(current_user: UserContext = Depends(get_current_user)):
    summary_data = AlertService.get_alerts_summary()
    return AlertsSummaryResponse(
        request_id=get_request_id(),
        **summary_data
    )

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    alert_item = AlertService.acknowledge_alert(alert_id, current_user.user_id)
    return AlertResponse(
        request_id=get_request_id(),
        alert=alert_item
    )

@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: str,
    data: Optional[ResolveAlertRequest] = None,
    current_user: UserContext = Depends(get_current_user)
):
    note = data.resolution_note if data else None
    alert_item = AlertService.resolve_alert(alert_id, current_user.user_id, note)
    return AlertResponse(
        request_id=get_request_id(),
        alert=alert_item
    )
