from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.common.schemas import AlertItem, AlertStatus, AlertSeverity
from app.common.errors import HireSenseException
from app.common.repositories import FirestoreBackedStore

# Default freshness threshold for stale profiles
STALE_THRESHOLD_DAYS = 30

# Firestore-backed alert store with no bootstrap data.
_alerts_db: Dict[str, Dict] = FirestoreBackedStore("alerts", {})

# Audit trail of alert lifecycle changes
_alert_events_db: Dict[str, Dict[str, Any]] = FirestoreBackedStore("alert_events", {})

_alert_counter = 0
_event_counter = 0

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _record_event(alert_id: str, from_status: Optional[str], to_status: str, changed_by: str, changed_at: str, notes: str):
    global _event_counter
    _event_counter += 1
    event_id = f"evt_{_event_counter:03d}"
    _alert_events_db[event_id] = {
        "event_id": event_id,
        "alert_id": alert_id,
        "from_status": from_status,
        "to_status": to_status,
        "changed_by": changed_by,
        "changed_at": changed_at,
        "notes": notes
    }

def _enum_value(val: Any) -> Any:
    return getattr(val, "value", val)

class AlertService:
    @staticmethod
    def list_alerts(
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> List[AlertItem]:
        AlertService.run_evaluation_sweep()
        items = []
        for alert in _alerts_db.values():
            if status and _enum_value(alert["status"]) != status:
                continue
            if alert_type and alert["alert_type"] != alert_type:
                continue
            if severity and _enum_value(alert["severity"]) != severity:
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

    @staticmethod
    def get_alerts_summary() -> Dict[str, Any]:
        AlertService.run_evaluation_sweep()
        active_count = 0
        acknowledged_count = 0
        resolved_count = 0
        by_severity = {AlertSeverity.HIGH.value: 0, AlertSeverity.MEDIUM.value: 0, AlertSeverity.LOW.value: 0}
        by_type = {}

        for alert in _alerts_db.values():
            status = _enum_value(alert["status"])
            severity = _enum_value(alert["severity"])
            alert_type = alert["alert_type"]

            if status == AlertStatus.ACTIVE.value:
                active_count += 1
                by_severity[severity] = by_severity.get(severity, 0) + 1
            elif status == AlertStatus.ACKNOWLEDGED.value:
                acknowledged_count += 1
                by_severity[severity] = by_severity.get(severity, 0) + 1
            elif status == AlertStatus.RESOLVED.value:
                resolved_count += 1

            if status in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value):
                by_type[alert_type] = by_type.get(alert_type, 0) + 1

        return {
            "active_count": active_count,
            "acknowledged_count": acknowledged_count,
            "resolved_count": resolved_count,
            "by_severity": by_severity,
            "by_type": by_type
        }

    @staticmethod
    def trigger_alert(
        alert_type: str,
        condition_key: str,
        source_entity_id: str,
        title: str,
        message: str,
        severity: AlertSeverity,
        job_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        ranking_id: Optional[str] = None
    ) -> Dict[str, Any]:
        global _alert_counter
        
        # Deduplication: Check if there is an active/acknowledged alert with same condition_key
        existing = None
        for alert in _alerts_db.values():
            if alert.get("condition_key") == condition_key and _enum_value(alert["status"]) in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value):
                existing = alert
                break
                
        now_str = _utc_now()
        if existing:
            existing["message"] = message
            existing["severity"] = severity
            existing["last_evaluated_at"] = now_str
            return existing

        _alert_counter += 1
        alert_id = f"alert_{alert_type.lower()}_{_alert_counter:03d}"
        
        new_alert = {
            "alert_id": alert_id,
            "alert_type": alert_type,
            "condition_key": condition_key,
            "source_entity_id": source_entity_id,
            "job_id": job_id,
            "candidate_id": candidate_id,
            "ranking_id": ranking_id,
            "status": AlertStatus.ACTIVE,
            "severity": severity,
            "title": title,
            "message": message,
            "created_at": now_str,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "resolved_at": None,
            "resolved_by": None,
            "resolution_note": None,
            "last_evaluated_at": now_str
        }
        
        _alerts_db[alert_id] = new_alert
        _record_event(alert_id, None, AlertStatus.ACTIVE.value, "system", now_str, "Alert created by system evaluation.")
        return new_alert

    @staticmethod
    def clear_alert(
        condition_key: str,
        resolution_note: str = "Condition cleared by system.",
        resolved_by: str = "system"
    ) -> Optional[Dict[str, Any]]:
        existing = None
        for alert in _alerts_db.values():
            if alert.get("condition_key") == condition_key and _enum_value(alert["status"]) in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value):
                existing = alert
                break
                
        if existing:
            now_str = _utc_now()
            from_status = _enum_value(existing["status"])
            existing["status"] = AlertStatus.RESOLVED
            existing["resolved_at"] = now_str
            existing["resolved_by"] = resolved_by
            existing["resolution_note"] = resolution_note
            existing["last_evaluated_at"] = now_str
            
            _record_event(existing["alert_id"], from_status, AlertStatus.RESOLVED.value, resolved_by, now_str, resolution_note)
            return existing
        return None

    @staticmethod
    def acknowledge_alert(alert_id: str, user_id: str) -> AlertItem:
        if alert_id not in _alerts_db:
            raise HireSenseException(
                status_code=404,
                code="ALERT_NOT_FOUND",
                message=f"Alert with ID {alert_id} was not found."
            )
            
        alert = _alerts_db[alert_id]
        if _enum_value(alert["status"]) != AlertStatus.ACTIVE.value:
            raise HireSenseException(
                status_code=400,
                code="INVALID_STATE",
                message="Only ACTIVE alerts can be acknowledged."
            )
            
        now_str = _utc_now()
        alert["status"] = AlertStatus.ACKNOWLEDGED
        alert["acknowledged_at"] = now_str
        alert["acknowledged_by"] = user_id
        alert["last_evaluated_at"] = now_str
        
        _record_event(alert_id, AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value, user_id, now_str, "Alert acknowledged by user.")
        
        return AlertItem(
            alert_id=alert["alert_id"],
            alert_type=alert["alert_type"],
            status=alert["status"],
            severity=alert["severity"],
            title=alert["title"],
            message=alert["message"],
            created_at=alert["created_at"],
            job_id=alert.get("job_id")
        )

    @staticmethod
    def resolve_alert(alert_id: str, user_id: str, resolution_note: Optional[str] = None) -> AlertItem:
        if alert_id not in _alerts_db:
            raise HireSenseException(
                status_code=404,
                code="ALERT_NOT_FOUND",
                message=f"Alert with ID {alert_id} was not found."
            )
            
        alert = _alerts_db[alert_id]
        if _enum_value(alert["status"]) == AlertStatus.RESOLVED.value:
            raise HireSenseException(
                status_code=400,
                code="INVALID_STATE",
                message="Alert is already RESOLVED."
            )
            
        now_str = _utc_now()
        from_status = _enum_value(alert["status"])
        alert["status"] = AlertStatus.RESOLVED
        alert["resolved_at"] = now_str
        alert["resolved_by"] = user_id
        alert["resolution_note"] = resolution_note or "Alert resolved manually."
        alert["last_evaluated_at"] = now_str
        
        _record_event(alert_id, from_status, AlertStatus.RESOLVED.value, user_id, now_str, alert["resolution_note"])
        
        return AlertItem(
            alert_id=alert["alert_id"],
            alert_type=alert["alert_type"],
            status=alert["status"],
            severity=alert["severity"],
            title=alert["title"],
            message=alert["message"],
            created_at=alert["created_at"],
            job_id=alert.get("job_id")
        )

    @staticmethod
    def run_evaluation_sweep():
        from app.modules.candidate.service import _candidates_db
        from app.modules.job.service import _jobs_db
        from app.modules.semantic_search.service import _embeddings_db
        from app.modules.ranking.service import _rankings_db
        
        now = datetime.now(timezone.utc)
        
        # 1. Candidate Stale Profiles
        for c_id, cand in _candidates_db.items():
            updated_at_str = cand.get("updated_at") or cand.get("created_at")
            if updated_at_str:
                try:
                    updated_at_val = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    diff_days = (now - updated_at_val).days
                    if diff_days >= STALE_THRESHOLD_DAYS:
                        AlertService.trigger_alert(
                            alert_type="STALE_PROFILE",
                            condition_key=f"STALE_PROFILE:CANDIDATE:{c_id}",
                            source_entity_id=c_id,
                            title=f"Profile is stale for candidate {cand.get('full_name')}",
                            message=f"Candidate profile has not been updated in {diff_days} days.",
                            severity=AlertSeverity.MEDIUM,
                            candidate_id=c_id
                        )
                    else:
                        AlertService.clear_alert(f"STALE_PROFILE:CANDIDATE:{c_id}", "Candidate profile updated, no longer stale.")
                except Exception:
                    pass
                    
        # 2. Job Stale Profiles
        for j_id, job in _jobs_db.items():
            updated_at_str = job.get("updated_at") or job.get("created_at")
            if updated_at_str:
                try:
                    updated_at_val = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    diff_days = (now - updated_at_val).days
                    if diff_days >= STALE_THRESHOLD_DAYS:
                        AlertService.trigger_alert(
                            alert_type="STALE_PROFILE",
                            condition_key=f"STALE_PROFILE:JOB:{j_id}",
                            source_entity_id=j_id,
                            title=f"Profile is stale for job {job.get('title')}",
                            message=f"Job profile has not been updated in {diff_days} days.",
                            severity=AlertSeverity.MEDIUM,
                            job_id=j_id
                        )
                    else:
                        AlertService.clear_alert(f"STALE_PROFILE:JOB:{j_id}", "Job profile updated, no longer stale.")
                except Exception:
                    pass
                    
        # 3. Parsing Failures
        for c_id, cand in _candidates_db.items():
            if cand.get("parsing_status") == "FAILED":
                AlertService.trigger_alert(
                    alert_type="RESUME_PARSE_FAILED",
                    condition_key=f"RESUME_PARSE_FAILED:{c_id}",
                    source_entity_id=c_id,
                    title=f"Resume parsing failed for candidate {c_id}",
                    message="The resume file could not be parsed into a valid candidate profile.",
                    severity=AlertSeverity.HIGH,
                    candidate_id=c_id
                )
            else:
                AlertService.clear_alert(f"RESUME_PARSE_FAILED:{c_id}", "Candidate reprocess succeeded.")
                
        for j_id, job in _jobs_db.items():
            if job.get("parsing_status") == "FAILED":
                AlertService.trigger_alert(
                    alert_type="JOB_PARSE_FAILED",
                    condition_key=f"JOB_PARSE_FAILED:{j_id}",
                    source_entity_id=j_id,
                    title=f"Job parsing failed for job {j_id}",
                    message="The job description could not be parsed into a valid job profile.",
                    severity=AlertSeverity.HIGH,
                    job_id=j_id
                )
            else:
                AlertService.clear_alert(f"JOB_PARSE_FAILED:{j_id}", "Job reprocess succeeded.")
                
        # 4. Embedding Failures
        for c_id in _candidates_db.keys():
            emb_id = f"emb_cand_{c_id}"
            emb = _embeddings_db.get(emb_id)
            if not emb or emb.get("status") == "FAILED":
                AlertService.trigger_alert(
                    alert_type="EMBEDDING_FAILED",
                    condition_key=f"EMBEDDING_FAILED:CANDIDATE:{c_id}",
                    source_entity_id=c_id,
                    title=f"Embedding refresh failed for candidate {c_id}",
                    message="Vector generation failed or vector metadata is missing.",
                    severity=AlertSeverity.HIGH,
                    candidate_id=c_id
                )
            else:
                AlertService.clear_alert(f"EMBEDDING_FAILED:CANDIDATE:{c_id}", "Embedding refresh completed successfully.")
                
        for j_id in _jobs_db.keys():
            emb_id = f"emb_job_{j_id}"
            emb = _embeddings_db.get(emb_id)
            if not emb or emb.get("status") == "FAILED":
                AlertService.trigger_alert(
                    alert_type="EMBEDDING_FAILED",
                    condition_key=f"EMBEDDING_FAILED:JOB:{j_id}",
                    source_entity_id=j_id,
                    title=f"Embedding refresh failed for job {j_id}",
                    message="Vector generation failed or vector metadata is missing.",
                    severity=AlertSeverity.HIGH,
                    job_id=j_id
                )
            else:
                AlertService.clear_alert(f"EMBEDDING_FAILED:JOB:{j_id}", "Embedding refresh completed successfully.")
                
        # 5. Rankings: Low Confidence & Anomaly
        for r_id, ranking in _rankings_db.items():
            candidates = ranking.get("candidates", [])
            any_low_conf = any(c.get("confidence_score", 1.0) < 0.65 for c in candidates)
            job_id = ranking.get("job_id")
            
            if any_low_conf:
                job_title = _jobs_db.get(job_id, {}).get("title", "Job") if job_id else "Job"
                AlertService.trigger_alert(
                    alert_type="LOW_CONFIDENCE_RANKING",
                    condition_key=f"LOW_CONFIDENCE_RANKING:{r_id}",
                    source_entity_id=r_id,
                    title=f"Ranking confidence is low for {job_title}",
                    message="Required skill evidence is incomplete for top candidates.",
                    severity=AlertSeverity.HIGH,
                    job_id=job_id,
                    ranking_id=r_id
                )
            else:
                AlertService.clear_alert(f"LOW_CONFIDENCE_RANKING:{r_id}", "Ranking refreshed and all confidence scores >= 0.65.")
                
            has_anomaly = False
            anomaly_msg = ""
            if candidates:
                top_cand = candidates[0]
                if top_cand.get("confidence_score", 1.0) < 0.65:
                    has_anomaly = True
                    anomaly_msg = "Top results collapsed into low-confidence scores."
                elif len(candidates) >= 3:
                    fit_scores = [c.get("fit_score", 0.0) for c in candidates]
                    if len(set(fit_scores)) == 1:
                        has_anomaly = True
                        anomaly_msg = "Ranking distribution deviates from expected thresholds (score collapse)."
                        
            if has_anomaly:
                AlertService.trigger_alert(
                    alert_type="RANKING_ANOMALY",
                    condition_key=f"RANKING_ANOMALY:{r_id}",
                    source_entity_id=r_id,
                    title=f"Ranking anomaly detected for run {r_id}",
                    message=anomaly_msg,
                    severity=AlertSeverity.MEDIUM,
                    job_id=job_id,
                    ranking_id=r_id
                )
            else:
                AlertService.clear_alert(f"RANKING_ANOMALY:{r_id}", "Anomaly no longer appears in evaluation.")
