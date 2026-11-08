"""
CloudSage Alert Lifecycle State Machine & Governance Service.
Manages formal status transitions: OPEN, ACKNOWLEDGED, INVESTIGATING, RESOLVED, SUPPRESSED, CLOSED.
Enforces mandatory resolution notes, suppression expiry, and records immutable audit logs.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from backend.app.core.enums import AlertStatus
from backend.app.models.alert import AlertHistory, AlertInstance


class InvalidAlertTransitionError(ValueError):
    """Raised when an illegal alert status transition is requested."""
    pass


class ResolutionNoteRequiredError(ValueError):
    """Raised when attempting to resolve an alert without required justification notes."""
    pass


VALID_ALERT_TRANSITIONS = {
    AlertStatus.OPEN.value: [
        AlertStatus.ACKNOWLEDGED.value,
        AlertStatus.INVESTIGATING.value,
        AlertStatus.RESOLVED.value,
        AlertStatus.SUPPRESSED.value,
        AlertStatus.CLOSED.value,
    ],
    AlertStatus.ACKNOWLEDGED.value: [
        AlertStatus.INVESTIGATING.value,
        AlertStatus.RESOLVED.value,
        AlertStatus.SUPPRESSED.value,
        AlertStatus.CLOSED.value,
    ],
    AlertStatus.INVESTIGATING.value: [
        AlertStatus.RESOLVED.value,
        AlertStatus.SUPPRESSED.value,
        AlertStatus.CLOSED.value,
    ],
    AlertStatus.RESOLVED.value: [
        AlertStatus.OPEN.value,
        AlertStatus.CLOSED.value,
    ],
    AlertStatus.SUPPRESSED.value: [
        AlertStatus.OPEN.value,
        AlertStatus.ACKNOWLEDGED.value,
        AlertStatus.INVESTIGATING.value,
        AlertStatus.CLOSED.value,
    ],
    AlertStatus.CLOSED.value: [
        AlertStatus.OPEN.value,
    ],
}


def transition_alert_status(
    db: Session,
    alert_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    actor: str = "system",
    notes: Optional[str] = None,
    ticket_ref: Optional[str] = None,
    suppress_hours: Optional[int] = None,
    auto_commit: bool = True,
    alert_instance_id: Optional[uuid.UUID] = None,
    new_status: Optional[str] = None,
) -> AlertInstance:
    """
    Executes an audited state transition on an AlertInstance.
    """
    target_id = alert_id or alert_instance_id
    if not target_id:
        raise ValueError("alert_id or alert_instance_id must be provided.")

    alert: Optional[AlertInstance] = db.query(AlertInstance).filter(AlertInstance.id == target_id).first()
    if not alert:
        raise ValueError(f"AlertInstance with ID '{target_id}' not found.")

    target_action = action or new_status or "ACKNOWLEDGE"
    if hasattr(target_action, "value"):
        target_action = target_action.value
    act = str(target_action).strip().upper()
    now = datetime.now(timezone.utc)
    prev_status = alert.status
    target_status = prev_status

    if act in ("ACKNOWLEDGE", "ACKNOWLEDGED"):
        target_status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_by = actor
        alert.acknowledged_at = now
        if ticket_ref:
            alert.ticket_ref = ticket_ref
        if notes:
            alert.investigation_notes = (alert.investigation_notes or "") + f"\n[{now.isoformat()}] Acknowledged: {notes}"

    elif act in ("INVESTIGATE", "INVESTIGATING"):
        target_status = AlertStatus.INVESTIGATING.value
        alert.investigated_by = actor
        if ticket_ref:
            alert.ticket_ref = ticket_ref
        if notes:
            alert.investigation_notes = (alert.investigation_notes or "") + f"\n[{now.isoformat()}] {notes}"

    elif act in ("RESOLVE", "RESOLVED"):
        if not notes or not notes.strip():
            raise ResolutionNoteRequiredError("A mandatory resolution explanation is required to resolve a cost alert.")
        target_status = AlertStatus.RESOLVED.value
        alert.resolved_by = actor
        alert.resolved_at = now
        alert.resolution_notes = notes.strip()

    elif act in ("SUPPRESS", "SUPPRESSED"):
        if not notes or not notes.strip():
            raise ValueError("A documented justification reason is required to suppress an alert.")
        hours = suppress_hours or 24
        if hours < 1:
            raise ValueError("Suppression duration must be at least 1 hour.")
        target_status = AlertStatus.SUPPRESSED.value
        alert.suppressed_by = actor
        alert.suppress_reason = notes.strip()
        alert.suppress_until = now + timedelta(hours=hours)

    elif act in ("REOPEN", "REOPENED"):
        target_status = AlertStatus.OPEN.value
        alert.suppress_until = None
        alert.resolved_at = None
        reopen_note = f"\n[{now.isoformat()}] Reopened by {actor}: {notes or 'Anomaly recurrent or ongoing.'}"
        alert.investigation_notes = (alert.investigation_notes or "") + reopen_note

    elif act in ("CLOSE", "CLOSED"):
        target_status = AlertStatus.CLOSED.value
        if notes:
            alert.investigation_notes = (alert.investigation_notes or "") + f"\n[{now.isoformat()}] Closed: {notes}"

    else:
        raise ValueError(f"Unsupported alert lifecycle action '{act}'. Valid actions: ACKNOWLEDGE, INVESTIGATE, RESOLVE, SUPPRESS, REOPEN, CLOSE.")

    # Validate transition state machine
    allowed = VALID_ALERT_TRANSITIONS.get(prev_status, [AlertStatus.OPEN.value])
    if target_status not in allowed and target_status != prev_status:
        raise InvalidAlertTransitionError(
            f"Cannot transition alert from '{prev_status}' to '{target_status}'. Allowed transitions: {allowed}"
        )

    alert.status = target_status
    alert.updated_at = now

    # Write audit log
    hist = AlertHistory(
        id=uuid.uuid4(),
        alert_instance_id=alert.id,
        from_status=prev_status,
        to_status=target_status,
        actor=actor,
        action=act,
        notes=notes,
        details={
            "ticket_ref": ticket_ref or alert.ticket_ref,
            "suppress_hours": suppress_hours,
        },
        created_at=now,
    )
    db.add(hist)

    if auto_commit:
        db.commit()
        db.refresh(alert)
    else:
        db.flush()

    return alert
