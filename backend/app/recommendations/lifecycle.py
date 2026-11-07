"""
CloudSage Recommendation Lifecycle State Machine.
Enforces valid state transitions, mandatory justification on dismissals/rejections,
and automated audit history logging in PostgreSQL.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from backend.app.core.enums import RecommendationStatus
from backend.app.models.recommendation import (
    Recommendation,
    RecommendationHistory,
)


VALID_TRANSITIONS: Dict[str, List[str]] = {
    "NEW": ["UNDER_REVIEW", "ACCEPTED", "APPROVED", "DISMISSED", "REJECTED"],
    "PROPOSED": ["UNDER_REVIEW", "ACCEPTED", "APPROVED", "DISMISSED", "REJECTED"],
    "UNDER_REVIEW": ["ENDORSED", "APPROVED", "ACCEPTED", "DISMISSED", "REJECTED"],
    "ENDORSED": ["APPROVED", "ACCEPTED", "DISMISSED", "REJECTED"],
    "ACCEPTED": ["IN_PROGRESS", "APPROVED", "DISMISSED", "REJECTED"],
    "APPROVED": ["IN_PROGRESS", "DISMISSED", "REJECTED"],
    "IN_PROGRESS": ["IMPLEMENTED", "APPROVED", "DISMISSED"],
    "IMPLEMENTED": ["VERIFIED", "REOPENED"],
    "DISMISSED": ["REOPENED"],
    "REJECTED": ["REOPENED"],
    "EXPIRED": ["REOPENED"],
    "VERIFIED": ["REOPENED"],
    "REOPENED": ["UNDER_REVIEW", "ACCEPTED", "APPROVED", "DISMISSED", "REJECTED"],
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is requested."""
    pass


class RejectionReasonRequiredError(ValueError):
    """Raised when dismissing or rejecting a recommendation without justification."""
    pass


def transition_recommendation_status(
    db: Session,
    recommendation_id: UUID,
    new_status: RecommendationStatus,
    actor: str,
    reason: Optional[str] = None,
    verified_savings: Optional[Decimal] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Recommendation:
    """
    Executes a formal lifecycle state transition on a recommendation.
    Validates rules, writes history audit log, and updates model timestamps.
    """
    rec: Optional[Recommendation] = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise ValueError(f"Recommendation with ID {recommendation_id} not found.")

    current_status = rec.status
    target_status = new_status.value if isinstance(new_status, RecommendationStatus) else str(new_status)

    # Check valid transition
    allowed = VALID_TRANSITIONS.get(current_status, ["REOPENED"])
    if target_status not in allowed and target_status != current_status:
        raise InvalidStateTransitionError(
            f"Cannot transition recommendation from '{current_status}' to '{target_status}'. "
            f"Allowed transitions: {allowed}"
        )

    # Mandatory reason for dismissal / rejection
    if target_status in ("DISMISSED", "REJECTED"):
        if not reason or not reason.strip():
            raise RejectionReasonRequiredError(
                f"A detailed justification reason is mandatory when transitioning to {target_status}."
            )

    now = datetime.now(timezone.utc)
    rec.status = target_status
    rec.updated_at = now

    action_label = f"STATUS_{target_status}"

    if target_status in ("APPROVED", "ACCEPTED"):
        rec.approved_by = actor
        rec.approved_at = now
        rec.accepted_at = now
        action_label = "APPROVED"
    elif target_status == "ENDORSED":
        rec.endorsed_by = actor
        action_label = "ENDORSED"
    elif target_status in ("DISMISSED", "REJECTED"):
        rec.reviewed_by = actor
        rec.reviewed_at = now
        rec.review_reason = reason
        action_label = "REJECTED" if target_status == "REJECTED" else "DISMISSED"
    elif target_status == "IMPLEMENTED":
        rec.implemented_at = now
        action_label = "IMPLEMENTED"
    elif target_status == "VERIFIED":
        rec.verified_at = now
        rec.verified_savings = verified_savings if verified_savings is not None else rec.estimated_monthly_savings
        action_label = "VERIFIED"
    elif target_status == "REOPENED":
        action_label = "REOPENED"

    # Write audit history
    history_entry = RecommendationHistory(
        recommendation_id=rec.id,
        from_status=current_status,
        to_status=target_status,
        actor=actor,
        action=action_label,
        notes=reason,
        details=metadata or {},
        created_at=now,
    )
    db.add(history_entry)
    db.commit()
    db.refresh(rec)
    return rec
