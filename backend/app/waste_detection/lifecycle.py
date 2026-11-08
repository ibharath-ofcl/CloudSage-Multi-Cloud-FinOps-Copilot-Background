"""
CloudSage Waste Finding Lifecycle & Triage State Machine.
Provides enterprise triage workflows: Acknowledge, Assign, Snooze, Dismiss, Resolve, and Reopen,
with batch action support, operational notes, and audit timestamps.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from backend.app.core.enums import WasteStatus
from backend.app.models.waste import WasteDetection


VALID_WASTE_TRANSITIONS: Dict[str, List[str]] = {
    "ACTIVE": ["ACKNOWLEDGED", "ASSIGNED", "SNOOZED", "DISMISSED", "RESOLVED"],
    "OPEN": ["ACKNOWLEDGED", "ASSIGNED", "SNOOZED", "DISMISSED", "RESOLVED"],
    "ACKNOWLEDGED": ["ASSIGNED", "SNOOZED", "DISMISSED", "RESOLVED", "REOPENED"],
    "ASSIGNED": ["ACKNOWLEDGED", "SNOOZED", "DISMISSED", "RESOLVED"],
    "SNOOZED": ["ACTIVE", "OPEN", "ACKNOWLEDGED", "DISMISSED", "RESOLVED", "REOPENED"],
    "DISMISSED": ["REOPENED"],
    "RESOLVED": ["REOPENED"],
    "REOPENED": ["ACKNOWLEDGED", "ASSIGNED", "SNOOZED", "DISMISSED", "RESOLVED"],
}


class InvalidWasteTransitionError(ValueError):
    """Raised when an illegal waste lifecycle transition is attempted."""
    pass


class WasteJustificationRequiredError(ValueError):
    """Raised when dismissal or resolution is performed without required justification."""
    pass


def transition_waste_status(
    db: Session,
    finding_id: UUID,
    action: str,
    actor: str,
    reason: Optional[str] = None,
    snooze_days: Optional[int] = None,
    assigned_to: Optional[str] = None,
    auto_commit: bool = True,
) -> WasteDetection:
    """
    Executes a formal lifecycle action on a waste finding.
    Supports ACKNOWLEDGE, ASSIGN, SNOOZE, DISMISS, RESOLVE, REOPEN.
    """
    finding: Optional[WasteDetection] = db.query(WasteDetection).filter(WasteDetection.id == finding_id).first()
    if not finding:
        raise ValueError(f"Waste finding with ID {finding_id} not found.")

    action_upper = action.upper().strip()
    now = datetime.now(timezone.utc)

    # Map action to target status
    action_status_map = {
        "ACKNOWLEDGE": "ACKNOWLEDGED",
        "ACKNOWLEDGED": "ACKNOWLEDGED",
        "ASSIGN": finding.status if finding.status in ("ACKNOWLEDGED", "ACTIVE", "OPEN") else "ACKNOWLEDGED",
        "SNOOZE": "SNOOZED",
        "SNOOZED": "SNOOZED",
        "DISMISS": "DISMISSED",
        "DISMISSED": "DISMISSED",
        "RESOLVE": "RESOLVED",
        "RESOLVED": "RESOLVED",
        "REOPEN": "REOPENED",
        "REOPENED": "REOPENED",
    }

    target_status = action_status_map.get(action_upper)
    if not target_status:
        raise InvalidWasteTransitionError(f"Unknown waste triage action: '{action}'")

    current_status = finding.status
    allowed = VALID_WASTE_TRANSITIONS.get(current_status, ["REOPENED", "ACKNOWLEDGED"])
    if target_status not in allowed and target_status != current_status:
        raise InvalidWasteTransitionError(
            f"Cannot transition waste finding from '{current_status}' to '{target_status}'. "
            f"Allowed transitions: {allowed}"
        )

    # Enforce mandatory justification
    if target_status in ("DISMISSED", "RESOLVED") and action_upper in ("DISMISS", "DISMISSED", "RESOLVE", "RESOLVED"):
        if not reason or not reason.strip():
            raise WasteJustificationRequiredError(
                f"A justification reason is mandatory when performing {action_upper} on a waste finding."
            )

    finding.status = target_status
    finding.last_evaluated_at = now

    if reason:
        finding.action_notes = reason.strip()

    if action_upper in ("ASSIGN",) and assigned_to:
        finding.assigned_to = assigned_to

    if assigned_to is not None and action_upper != "ASSIGN":
        finding.assigned_to = assigned_to

    if target_status == "DISMISSED":
        finding.dismissed_by = actor
        finding.dismissal_reason = reason.strip() if reason else None
    elif target_status == "RESOLVED":
        finding.resolved_by = actor
        finding.resolved_at = now
    elif target_status == "SNOOZED":
        days = snooze_days if snooze_days and snooze_days > 0 else 14
        finding.snooze_until = now + timedelta(days=days)
        finding.dismissed_by = actor
        finding.dismissal_reason = reason or f"Snoozed for {days} days"
    elif target_status == "REOPENED":
        finding.reopened_by = actor
        finding.reopened_at = now
        finding.snooze_until = None

    if auto_commit:
        db.commit()
    else:
        db.flush()
    db.refresh(finding)
    return finding


def batch_transition_waste(
    db: Session,
    finding_ids: List[UUID],
    action: str,
    actor: str,
    reason: Optional[str] = None,
    snooze_days: Optional[int] = None,
    assigned_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes atomic batch triage actions across multiple waste findings with error isolation.
    """
    successful: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for f_id in finding_ids:
        try:
            with db.begin_nested():
                updated = transition_waste_status(
                    db=db,
                    finding_id=f_id,
                    action=action,
                    actor=actor,
                    reason=reason,
                    snooze_days=snooze_days,
                    assigned_to=assigned_to,
                    auto_commit=False,
                )
                successful.append({
                    "id": str(updated.id),
                    "resource_id": updated.resource_id,
                    "status": updated.status,
                    "assigned_to": updated.assigned_to,
                    "estimated_monthly_waste": float(updated.estimated_monthly_waste),
                })
        except Exception as e:
            failed.append({
                "id": str(f_id),
                "error": str(e),
            })

    db.commit()
    return {
        "total_requested": len(finding_ids),
        "total_successful": len(successful),
        "total_failed": len(failed),
        "successful": successful,
        "failed": failed,
    }
