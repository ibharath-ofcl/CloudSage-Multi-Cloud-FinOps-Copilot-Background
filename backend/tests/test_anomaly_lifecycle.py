"""
Unit Tests for CloudSage Cost Anomaly Lifecycle State Management.
Tests deduplication, in-place updates, auto-resolution on return to baseline,
reopening when spend surges again, and human review workflows.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.lifecycle import (
    check_and_auto_resolve,
    persist_or_update_anomaly,
    update_anomaly_status,
)
from backend.app.anomaly_detection.models import AnomalyCandidate
from backend.app.core.enums import AnomalyCategory, AnomalyStatus, Severity
from backend.app.models.anomaly import CostAnomaly


def test_persist_or_update_anomaly_creates_and_updates_in_place(db_session: Session):
    """Validates idempotent deduplication and in-place updating of active anomalies."""
    cand = AnomalyCandidate(
        detector_id="statistical_ensemble_detector",
        detector_version="1.0.0",
        provider="AWS",
        account_id="111122223333",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        anomaly_date=date(2026, 10, 10),
        observed_cost=Decimal("500.0000"),
        expected_cost=Decimal("100.0000"),
        absolute_deviation=Decimal("400.0000"),
        percentage_deviation=Decimal("400.0000"),
        estimated_excess_cost=Decimal("400.0000"),
        projected_monthly_impact=Decimal("400.0000"),
        severity=Severity.HIGH,
    )

    # 1. First run -> Creates
    res1 = persist_or_update_anomaly(db_session, cand)
    db_session.commit()
    assert res1["action"] == "created"
    assert res1["anomaly"].status == AnomalyStatus.DETECTED

    # 2. Second run with updated cost -> Updates in-place
    cand.observed_cost = Decimal("650.0000")
    cand.estimated_excess_cost = Decimal("550.0000")
    res2 = persist_or_update_anomaly(db_session, cand)
    db_session.commit()
    assert res2["action"] == "updated"
    assert res2["anomaly"].actual_cost == Decimal("650.0000")

    # Confirm exactly 1 record in database
    total = db_session.query(CostAnomaly).count()
    assert total == 1


def test_auto_resolution_when_spending_normalizes(db_session: Session):
    """Validates automatic resolution when spending falls back below upper fence."""
    cand = AnomalyCandidate(
        detector_id="service_cost_spike_detector",
        detector_version="1.0.0",
        provider="GCP",
        account_id="prj-prod-01",
        service_category="DATABASE",
        service_name="Cloud Spanner",
        region="us-central1",
        anomaly_date=date(2026, 10, 12),
        observed_cost=Decimal("400.0000"),
        expected_cost=Decimal("50.0000"),
        absolute_deviation=Decimal("350.0000"),
        percentage_deviation=Decimal("700.0000"),
        estimated_excess_cost=Decimal("350.0000"),
        projected_monthly_impact=Decimal("350.0000"),
    )
    res = persist_or_update_anomaly(db_session, cand)
    db_session.commit()
    anomaly_id = res["anomaly"].id

    # Auto-resolve check: current spend is $55, upper threshold is $80
    resolved = check_and_auto_resolve(
        db=db_session,
        provider="GCP",
        account_id="prj-prod-01",
        service_name="Cloud Spanner",
        current_cost=Decimal("55.0000"),
        expected_cost=Decimal("50.0000"),
        upper_threshold=Decimal("80.0000"),
    )
    db_session.commit()

    assert resolved == 1
    anom = db_session.query(CostAnomaly).filter(CostAnomaly.id == anomaly_id).first()
    assert anom.status == AnomalyStatus.RESOLVED
    assert anom.resolution_reason == "AUTO_RESOLVED_RETURN_TO_BASELINE"


def test_reopen_closed_anomaly_on_new_spike(db_session: Session):
    """Validates that a recurring spike reopens an already resolved anomaly."""
    cand = AnomalyCandidate(
        detector_id="resource_cost_spike_detector",
        detector_version="1.0.0",
        provider="AZURE",
        account_id="sub-001",
        service_category="COMPUTE",
        service_name="Virtual Machines",
        region="eastus",
        resource_id="/subscriptions/sub-001/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
        anomaly_date=date(2026, 10, 14),
        observed_cost=Decimal("300.0000"),
        expected_cost=Decimal("50.0000"),
        absolute_deviation=Decimal("250.0000"),
        percentage_deviation=Decimal("500.0000"),
        estimated_excess_cost=Decimal("250.0000"),
        projected_monthly_impact=Decimal("250.0000"),
        anomaly_category=AnomalyCategory.RESOURCE_SPIKE,
    )
    res = persist_or_update_anomaly(db_session, cand)
    db_session.commit()
    anom = res["anomaly"]

    # Manually resolve it
    update_anomaly_status(
        db=db_session,
        anomaly_id=anom.id,
        new_status=AnomalyStatus.RESOLVED,
        user="finops_engineer",
        reason="Turned off unneeded worker threads.",
    )

    # Re-evaluate with recurring spike -> should transition to REOPENED
    res2 = persist_or_update_anomaly(db_session, cand)
    db_session.commit()

    assert res2["action"] == "reopened"
    assert res2["anomaly"].status == AnomalyStatus.REOPENED
    assert res2["anomaly"].reopened_at is not None


def test_human_review_status_transitions(db_session: Session):
    """Validates analyst workflow transitions and required rationale validations."""
    cand = AnomalyCandidate(
        detector_id="change_point_detector",
        detector_version="1.0.0",
        provider="AWS",
        account_id="111122223333",
        service_category="STORAGE",
        service_name="AmazonS3",
        region="us-east-1",
        anomaly_date=date(2026, 10, 15),
        observed_cost=Decimal("150.0000"),
        expected_cost=Decimal("30.0000"),
        absolute_deviation=Decimal("120.0000"),
        percentage_deviation=Decimal("400.0000"),
        estimated_excess_cost=Decimal("120.0000"),
        projected_monthly_impact=Decimal("3600.0000"),
    )
    res = persist_or_update_anomaly(db_session, cand)
    db_session.commit()
    anom_id = res["anomaly"].id

    # 1. Transition to ACKNOWLEDGED
    updated = update_anomaly_status(
        db=db_session,
        anomaly_id=anom_id,
        new_status=AnomalyStatus.ACKNOWLEDGED,
        user="analyst1",
        notes="Investigating data migration job.",
    )
    assert updated.status == AnomalyStatus.ACKNOWLEDGED
    assert "Investigating data migration job" in updated.investigation_notes

    # 2. Transition to DISMISSED without reason must fail
    with pytest.raises(ValueError, match="dismissal_reason is required"):
        update_anomaly_status(
            db=db_session,
            anomaly_id=anom_id,
            new_status=AnomalyStatus.DISMISSED,
            user="analyst1",
            reason=None,
        )

    # 3. Transition to DISMISSED with reason succeeds
    dismissed = update_anomaly_status(
        db=db_session,
        anomaly_id=anom_id,
        new_status=AnomalyStatus.DISMISSED,
        user="lead_architect",
        reason="Approved quarterly data archival migration.",
    )
    assert dismissed.status == AnomalyStatus.DISMISSED
    assert dismissed.dismissal_reason == "Approved quarterly data archival migration."
    assert dismissed.dismissed_by == "lead_architect"

