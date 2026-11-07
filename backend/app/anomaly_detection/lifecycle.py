"""
CloudSage Anomaly Lifecycle State Manager.
Handles deduplication, in-place updates, auto-resolution when costs normalize,
reopening when spend resurges, and human review transitions.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.models import AnomalyCandidate
from backend.app.core.enums import AnomalyCategory, AnomalyStatus
from backend.app.models.anomaly import CostAnomaly


def make_json_serializable(obj: Any) -> Any:
    """Recursively converts Decimals to strings for JSON/JSONB serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    return obj


def persist_or_update_anomaly(
    db: Session,
    candidate: AnomalyCandidate,
) -> Dict[str, Any]:
    """
    Persists a new anomaly candidate or updates an existing record in-place.
    Guarantees idempotency based on (provider, account_id, service_name, resource_id, anomaly_date, anomaly_category).
    Handles reopening of previously resolved or dismissed anomalies if spend remains high.
    """
    now = datetime.now(timezone.utc)
    b_metrics = make_json_serializable(candidate.baseline_metrics)
    rc_analysis = make_json_serializable(candidate.root_cause_analysis)
    contrib_res = make_json_serializable(candidate.contributing_resources)
    billing_refs = make_json_serializable(candidate.source_billing_references)

    # Search for existing anomaly with matching natural key
    query = db.query(CostAnomaly).filter(
        CostAnomaly.provider == candidate.provider,
        CostAnomaly.account_id == candidate.account_id,
        CostAnomaly.anomaly_date == candidate.anomaly_date,
        CostAnomaly.anomaly_category == candidate.anomaly_category,
    )

    if candidate.service_name:
        query = query.filter(CostAnomaly.service_name == candidate.service_name)
    if candidate.resource_id:
        query = query.filter(CostAnomaly.resource_id == candidate.resource_id)
    else:
        query = query.filter(CostAnomaly.resource_id.is_(None))

    existing: Optional[CostAnomaly] = query.first()

    if existing:
        # Update existing anomaly in-place
        existing.detector_id = candidate.detector_id
        existing.detector_version = candidate.detector_version
        existing.actual_cost = candidate.observed_cost
        existing.expected_cost = candidate.expected_cost
        existing.absolute_deviation = candidate.absolute_deviation
        existing.spike_percentage = candidate.percentage_deviation
        existing.z_score = candidate.z_score
        existing.estimated_excess_cost = candidate.estimated_excess_cost
        existing.projected_monthly_impact = candidate.projected_monthly_impact
        existing.severity = candidate.severity
        existing.confidence_score = candidate.confidence_score
        existing.baseline_metrics = b_metrics
        existing.root_cause_analysis = rc_analysis
        existing.contributing_resources = contrib_res
        existing.source_billing_references = billing_refs
        existing.explanation = candidate.explanation or existing.explanation
        existing.title = candidate.title or existing.title
        existing.last_detected_at = now

        # Reopen if previously closed but anomalous again
        was_closed = existing.status in (AnomalyStatus.RESOLVED, AnomalyStatus.DISMISSED)
        if was_closed and candidate.estimated_excess_cost > Decimal("0.0000"):
            existing.status = AnomalyStatus.REOPENED
            existing.reopened_at = now
            action = "reopened"
        else:
            action = "updated"

        db.flush()
        return {"action": action, "anomaly": existing}

    # Create new CostAnomaly
    det_methods = [m.value for m in candidate.detection_methods]
    method_str = det_methods[0] if det_methods else "Z_SCORE"

    new_anomaly = CostAnomaly(
        provider=candidate.provider,
        account_id=candidate.account_id,
        service_category=candidate.service_category,
        service_name=candidate.service_name,
        region=candidate.region,
        resource_id=candidate.resource_id,
        sku=candidate.sku,
        anomaly_category=candidate.anomaly_category,
        anomaly_date=candidate.anomaly_date,
        detection_method=method_str,
        detector_id=candidate.detector_id,
        detector_version=candidate.detector_version,
        title=candidate.title or f"Cost Anomaly on {candidate.provider} {candidate.service_name or 'Spend'}",
        explanation=candidate.explanation or "Identified unusual expenditure deviation.",
        actual_cost=candidate.observed_cost,
        expected_cost=candidate.expected_cost,
        absolute_deviation=candidate.absolute_deviation,
        spike_percentage=candidate.percentage_deviation,
        z_score=candidate.z_score,
        estimated_excess_cost=candidate.estimated_excess_cost,
        projected_monthly_impact=candidate.projected_monthly_impact,
        currency=candidate.currency,
        status=AnomalyStatus.DETECTED,
        severity=candidate.severity,
        confidence_score=candidate.confidence_score,
        baseline_window_days=candidate.baseline_window_days,
        observation_window_days=candidate.observation_window_days,
        baseline_metrics=b_metrics,
        root_cause_analysis=rc_analysis,
        contributing_resources=contrib_res,
        source_billing_references=billing_refs,
        first_detected_at=now,
        last_detected_at=now,
    )

    db.add(new_anomaly)
    db.flush()
    return {"action": "created", "anomaly": new_anomaly}


def check_and_auto_resolve(
    db: Session,
    provider: str,
    account_id: str,
    service_name: str,
    current_cost: Decimal,
    expected_cost: Decimal,
    upper_threshold: Decimal,
) -> int:
    """
    Checks open anomalies for the given dimension and auto-resolves them if current cost
    has returned below the upper baseline threshold.
    """
    if current_cost > upper_threshold:
        return 0

    now = datetime.now(timezone.utc)
    open_statuses = [
        AnomalyStatus.DETECTED,
        AnomalyStatus.INVESTIGATING,
        AnomalyStatus.ACKNOWLEDGED,
        AnomalyStatus.REOPENED,
    ]

    open_anomalies = db.query(CostAnomaly).filter(
        CostAnomaly.provider == provider,
        CostAnomaly.account_id == account_id,
        CostAnomaly.service_name == service_name,
        CostAnomaly.status.in_(open_statuses),
    ).all()

    resolved_count = 0
    for anom in open_anomalies:
        anom.status = AnomalyStatus.RESOLVED
        anom.resolution_reason = "AUTO_RESOLVED_RETURN_TO_BASELINE"
        anom.resolved_by = "CloudSage_Autonomous_Engine"
        anom.investigation_notes = (
            f"Auto-resolved at {now.isoformat()}: spending returned to normal "
            f"(${current_cost:,.2f} <= threshold ${upper_threshold:,.2f})."
        )
        resolved_count += 1

    if resolved_count > 0:
        db.flush()

    return resolved_count


def update_anomaly_status(
    db: Session,
    anomaly_id: Any,
    new_status: AnomalyStatus,
    user: str = "finops_analyst",
    reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> CostAnomaly:
    """
    Handles engineer/analyst state transitions (ACKNOWLEDGE, INVESTIGATE, DISMISS, RESOLVE, REOPEN).
    Validates required reasons and records audit metadata.
    """
    target_id = anomaly_id
    if isinstance(anomaly_id, str):
        try:
            import uuid
            target_id = uuid.UUID(anomaly_id)
        except Exception:
            target_id = anomaly_id

    anomaly = db.query(CostAnomaly).filter(CostAnomaly.id == target_id).first()
    if not anomaly:
        raise ValueError(f"CostAnomaly with id {anomaly_id} not found.")

    now = datetime.now(timezone.utc)
    anomaly.status = new_status

    if new_status == AnomalyStatus.DISMISSED:
        if not reason:
            raise ValueError("A dismissal_reason is required when dismissing an anomaly.")
        anomaly.dismissal_reason = reason
        anomaly.dismissed_by = user

    elif new_status == AnomalyStatus.RESOLVED:
        if not reason:
            raise ValueError("A resolution_reason is required when resolving an anomaly.")
        anomaly.resolution_reason = reason
        anomaly.resolved_by = user

    elif new_status == AnomalyStatus.REOPENED:
        anomaly.reopened_at = now

    if notes:
        existing_notes = anomaly.investigation_notes or ""
        timestamp_prefix = f"[{now.strftime('%Y-%m-%d %H:%M:%S UTC')} by {user}]"
        anomaly.investigation_notes = f"{existing_notes}\n{timestamp_prefix}: {notes}".strip()

    db.commit()
    db.refresh(anomaly)
    return anomaly
