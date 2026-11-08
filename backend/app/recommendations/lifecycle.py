"""
CloudSage Recommendation Lifecycle State Machine & Governance.
Enforces valid state transitions, mandatory justification on dismissals/rejections,
automated audit history logging, batch review operations, and savings override governance.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid

from sqlalchemy.orm import Session
from backend.app.core.enums import RecommendationStatus
from backend.app.models.recommendation import (
    Recommendation,
    RecommendationHistory,
    RecommendationSavingsOverride,
)


VALID_TRANSITIONS: Dict[str, List[str]] = {
    "NEW": ["UNDER_REVIEW", "ACCEPTED", "APPROVED", "DISMISSED", "REJECTED", "SNOOZED"],
    "PROPOSED": ["UNDER_REVIEW", "ACCEPTED", "APPROVED", "DISMISSED", "REJECTED", "SNOOZED"],
    "UNDER_REVIEW": ["ENDORSED", "APPROVED", "ACCEPTED", "DISMISSED", "REJECTED", "SNOOZED"],
    "ENDORSED": ["APPROVED", "ACCEPTED", "DISMISSED", "REJECTED", "SNOOZED"],
    "ACCEPTED": ["IN_PROGRESS", "APPROVED", "DISMISSED", "REJECTED", "SNOOZED"],
    "APPROVED": ["IN_PROGRESS", "DISMISSED", "REJECTED", "SNOOZED"],
    "IN_PROGRESS": ["IMPLEMENTED", "APPROVED", "DISMISSED"],
    "IMPLEMENTED": ["VERIFIED", "REOPENED"],
    "DISMISSED": ["REOPENED"],
    "REJECTED": ["REOPENED"],
    "EXPIRED": ["REOPENED"],
    "VERIFIED": ["REOPENED"],
    "SNOOZED": ["PROPOSED", "UNDER_REVIEW", "APPROVED", "DISMISSED", "REJECTED", "REOPENED"],
    "REOPENED": ["UNDER_REVIEW", "ACCEPTED", "APPROVED", "DISMISSED", "REJECTED", "SNOOZED"],
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is requested."""
    pass


class RejectionReasonRequiredError(ValueError):
    """Raised when dismissing or rejecting a recommendation without justification."""
    pass


class DualCustodyViolationError(ValueError):
    """Raised when proposer attempts to approve their own override without permission."""
    pass


def transition_recommendation_status(
    db: Session,
    recommendation_id: UUID,
    new_status: RecommendationStatus,
    actor: str,
    reason: Optional[str] = None,
    verified_savings: Optional[Decimal] = None,
    metadata: Optional[Dict[str, Any]] = None,
    snooze_days: Optional[int] = None,
    assigned_to: Optional[str] = None,
    external_ticket_ref: Optional[str] = None,
    auto_commit: bool = True,
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
    elif target_status == "SNOOZED":
        days = snooze_days if snooze_days and snooze_days > 0 else 14
        rec.snooze_until = now + timedelta(days=days)
        rec.reviewed_by = actor
        rec.reviewed_at = now
        rec.review_reason = reason or f"Snoozed for {days} days"
        action_label = "SNOOZED"
    elif target_status == "IMPLEMENTED":
        rec.implemented_at = now
        action_label = "IMPLEMENTED"
    elif target_status == "VERIFIED":
        rec.verified_at = now
        rec.verified_savings = verified_savings if verified_savings is not None else rec.estimated_monthly_savings
        action_label = "VERIFIED"
    elif target_status == "REOPENED":
        rec.snooze_until = None
        action_label = "REOPENED"

    if assigned_to is not None:
        rec.assigned_to = assigned_to
    if external_ticket_ref is not None:
        rec.external_ticket_ref = external_ticket_ref

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
    if auto_commit:
        db.commit()
    else:
        db.flush()
    db.refresh(rec)
    return rec


def batch_transition_recommendations(
    db: Session,
    recommendation_ids: List[UUID],
    new_status: RecommendationStatus,
    actor: str,
    reason: Optional[str] = None,
    snooze_days: Optional[int] = None,
    assigned_to: Optional[str] = None,
    external_ticket_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes atomic batch status transitions across multiple recommendations.
    Provides graceful error handling for partial failures and returns detailed execution report.
    """
    successful: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for rec_id in recommendation_ids:
        try:
            # Use nested transaction / savepoint for each item
            with db.begin_nested():
                updated = transition_recommendation_status(
                    db=db,
                    recommendation_id=rec_id,
                    new_status=new_status,
                    actor=actor,
                    reason=reason,
                    snooze_days=snooze_days,
                    assigned_to=assigned_to,
                    external_ticket_ref=external_ticket_ref,
                    auto_commit=False,
                )
                successful.append({
                    "id": str(updated.id),
                    "status": updated.status,
                    "title": updated.title,
                    "estimated_monthly_savings": float(updated.estimated_monthly_savings),
                })
        except Exception as e:
            failed.append({
                "id": str(rec_id),
                "error": str(e),
            })

    db.commit()
    return {
        "total_requested": len(recommendation_ids),
        "total_successful": len(successful),
        "total_failed": len(failed),
        "successful": successful,
        "failed": failed,
    }


def propose_savings_override(
    db: Session,
    recommendation_id: UUID,
    proposed_monthly_savings: Decimal,
    reason: str,
    proposed_by: str,
) -> RecommendationSavingsOverride:
    """
    Proposes a revised savings figure for an optimization recommendation, initiating
    formal FinOps dual-custody review.
    """
    rec: Optional[Recommendation] = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise ValueError(f"Recommendation with ID {recommendation_id} not found.")

    if not reason or not reason.strip():
        raise ValueError("A documented engineering / FinOps justification is required for savings override.")

    if proposed_monthly_savings < Decimal("0.0000"):
        raise ValueError("Proposed savings cannot be negative.")

    override = RecommendationSavingsOverride(
        id=uuid.uuid4(),
        recommendation_id=rec.id,
        original_monthly_savings=rec.estimated_monthly_savings,
        proposed_monthly_savings=proposed_monthly_savings,
        reason=reason.strip(),
        proposed_by=proposed_by,
        status="PROPOSED",
    )
    db.add(override)

    # Log history on recommendation
    now = datetime.now(timezone.utc)
    hist = RecommendationHistory(
        id=uuid.uuid4(),
        recommendation_id=rec.id,
        from_status=rec.status,
        to_status=rec.status,
        actor=proposed_by,
        action="SAVINGS_OVERRIDE_PROPOSED",
        notes=f"Proposed savings adjustment from ${rec.estimated_monthly_savings} to ${proposed_monthly_savings}: {reason}",
        details={
            "override_id": str(override.id),
            "original_savings": str(rec.estimated_monthly_savings),
            "proposed_savings": str(proposed_monthly_savings),
        },
        created_at=now,
    )
    db.add(hist)
    db.commit()
    db.refresh(override)
    return override


def review_savings_override(
    db: Session,
    override_id: UUID,
    approved_by: str,
    approve: bool,
    rejection_reason: Optional[str] = None,
    enforce_dual_custody: bool = False,
) -> RecommendationSavingsOverride:
    """
    Formally approves or rejects a proposed savings override.
    When approved, updates the recommendation's revised_monthly_savings and marks is_savings_overridden=True.
    """
    override: Optional[RecommendationSavingsOverride] = db.query(
        RecommendationSavingsOverride
    ).filter(RecommendationSavingsOverride.id == override_id).first()

    if not override:
        raise ValueError(f"Savings override with ID {override_id} not found.")

    if override.status != "PROPOSED":
        raise ValueError(f"Cannot review override in '{override.status}' state. Only 'PROPOSED' overrides can be reviewed.")

    if enforce_dual_custody and override.proposed_by.lower() == approved_by.lower():
        raise DualCustodyViolationError("Proposer cannot approve their own savings override under dual custody rules.")

    now = datetime.now(timezone.utc)
    rec = override.recommendation

    if approve:
        override.status = "APPROVED"
        override.approved_by = approved_by
        override.reviewed_at = now

        # Update recommendation
        rec.revised_monthly_savings = override.proposed_monthly_savings
        rec.is_savings_overridden = True
        rec.estimated_annual_savings = (override.proposed_monthly_savings * Decimal("12")).quantize(Decimal("0.0001"))
        rec.updated_at = now

        hist = RecommendationHistory(
            id=uuid.uuid4(),
            recommendation_id=rec.id,
            from_status=rec.status,
            to_status=rec.status,
            actor=approved_by,
            action="SAVINGS_OVERRIDE_APPROVED",
            notes=f"Approved savings override to ${override.proposed_monthly_savings} USD/mo.",
            details={
                "override_id": str(override.id),
                "original_monthly_savings": str(override.original_monthly_savings),
                "revised_monthly_savings": str(override.proposed_monthly_savings),
            },
            created_at=now,
        )
        db.add(hist)
    else:
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection justification reason is mandatory when rejecting a savings override.")
        override.status = "REJECTED"
        override.approved_by = approved_by
        override.rejection_reason = rejection_reason.strip()
        override.reviewed_at = now

        hist = RecommendationHistory(
            id=uuid.uuid4(),
            recommendation_id=rec.id,
            from_status=rec.status,
            to_status=rec.status,
            actor=approved_by,
            action="SAVINGS_OVERRIDE_REJECTED",
            notes=f"Rejected savings override: {rejection_reason}",
            details={
                "override_id": str(override.id),
                "proposed_savings": str(override.proposed_monthly_savings),
            },
            created_at=now,
        )
        db.add(hist)

    db.commit()
    db.refresh(override)
    return override
