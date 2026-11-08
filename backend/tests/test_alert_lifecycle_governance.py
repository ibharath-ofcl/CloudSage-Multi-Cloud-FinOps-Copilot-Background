"""
Unit and Integration Tests for Alert Lifecycle State Machine and Governance.
Tests state transitions (Acknowledge, Investigate, Resolve, Suppress, Reopen, Close),
mandatory notes validation, and complete audit history logging.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import AlertStatus, Severity
from backend.app.models.alert import AlertHistory, AlertInstance
from backend.app.models.anomaly import CostAnomaly
from backend.app.alerts.lifecycle import transition_alert_status


def create_base_alert(db_session, status: str = AlertStatus.OPEN.value) -> AlertInstance:
    now = datetime.now(timezone.utc)
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="Amazon Elastic Compute Cloud",
        region="us-east-1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.HIGH,
        actual_cost=Decimal("600.0000"),
        expected_cost=Decimal("300.0000"),
        estimated_excess_cost=Decimal("300.0000"),
        spike_percentage=Decimal("100.00"),
    )
    db_session.add(anomaly)
    db_session.flush()

    alert = AlertInstance(
        id=uuid.uuid4(),
        anomaly_id=anomaly.id,
        dedup_key=f"acct:AWS:123:EC2:us-east-1:{uuid.uuid4()}",
        title="High EC2 Spend Anomaly Alert",
        severity=Severity.HIGH.value,
        status=status,
        provider="AWS",
        account_id="123456789012",
        service_name="Amazon Elastic Compute Cloud",
        region="us-east-1",
        current_cost=Decimal("600.0000"),
        expected_cost=Decimal("300.0000"),
        excess_cost=Decimal("300.0000"),
        percentage_deviation=Decimal("100.00"),
        first_triggered_at=now,
        last_triggered_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


def test_transition_acknowledge(db_session):
    """Verifies transition from OPEN to ACKNOWLEDGED."""
    alert = create_base_alert(db_session, status=AlertStatus.OPEN.value)

    updated = transition_alert_status(
        db=db_session,
        alert_instance_id=alert.id,
        action="ACKNOWLEDGE",
        actor="lead-finops@company.com",
        notes="Triaging with cloud infrastructure team",
        ticket_ref="JIRA-1001",
    )

    assert updated.status == AlertStatus.ACKNOWLEDGED.value
    assert updated.acknowledged_by == "lead-finops@company.com"
    assert updated.acknowledged_at is not None
    assert updated.ticket_ref == "JIRA-1001"

    # Verify history entry
    hist = (
        db_session.query(AlertHistory)
        .filter(AlertHistory.alert_instance_id == alert.id)
        .first()
    )
    assert hist is not None
    assert hist.action == "ACKNOWLEDGE"
    assert hist.actor == "lead-finops@company.com"
    assert hist.notes == "Triaging with cloud infrastructure team"


def test_transition_investigate(db_session):
    """Verifies transition to INVESTIGATING status with notes."""
    alert = create_base_alert(db_session, status=AlertStatus.ACKNOWLEDGED.value)

    updated = transition_alert_status(
        db=db_session,
        alert_instance_id=alert.id,
        action="INVESTIGATE",
        actor="cloud-engineer@company.com",
        notes="Checking Kubernetes pod autoscale surge",
    )

    assert updated.status == AlertStatus.INVESTIGATING.value
    assert updated.investigated_by == "cloud-engineer@company.com"
    assert "Checking Kubernetes pod autoscale surge" in updated.investigation_notes


def test_transition_resolve_requires_notes(db_session):
    """Verifies that resolving an alert requires mandatory resolution notes."""
    alert = create_base_alert(db_session, status=AlertStatus.INVESTIGATING.value)

    # Missing notes should raise ValueError
    with pytest.raises(ValueError, match="mandatory resolution explanation is required"):
        transition_alert_status(
            db=db_session,
            alert_instance_id=alert.id,
            action="RESOLVE",
            actor="admin@company.com",
            notes=None,
        )

    with pytest.raises(ValueError, match="mandatory resolution explanation is required"):
        transition_alert_status(
            db=db_session,
            alert_instance_id=alert.id,
            action="RESOLVE",
            actor="admin@company.com",
            notes="   ",
        )


def test_transition_resolve_success(db_session):
    """Verifies successful resolution with mandatory notes."""
    alert = create_base_alert(db_session, status=AlertStatus.INVESTIGATING.value)

    updated = transition_alert_status(
        db=db_session,
        alert_instance_id=alert.id,
        action="RESOLVE",
        actor="admin@company.com",
        notes="Downscaled unneeded staging cluster instances.",
    )

    assert updated.status == AlertStatus.RESOLVED.value
    assert updated.resolved_by == "admin@company.com"
    assert updated.resolved_at is not None
    assert updated.resolution_notes == "Downscaled unneeded staging cluster instances."


def test_transition_suppress_requires_reason(db_session):
    """Verifies that suppressing an alert requires suppression reason."""
    alert = create_base_alert(db_session, status=AlertStatus.OPEN.value)

    with pytest.raises(ValueError, match="documented justification reason is required"):
        transition_alert_status(
            db=db_session,
            alert_instance_id=alert.id,
            action="SUPPRESS",
            actor="admin@company.com",
            notes=None,
        )


def test_transition_suppress_success(db_session):
    """Verifies suppressing an alert sets suppress_until correctly."""
    alert = create_base_alert(db_session, status=AlertStatus.OPEN.value)

    updated = transition_alert_status(
        db=db_session,
        alert_instance_id=alert.id,
        action="SUPPRESS",
        actor="sre-oncall@company.com",
        notes="Planned performance benchmark load test",
        suppress_hours=48,
    )

    assert updated.status == AlertStatus.SUPPRESSED.value
    assert updated.suppressed_by == "sre-oncall@company.com"
    assert updated.suppress_reason == "Planned performance benchmark load test"
    assert updated.suppress_until is not None


def test_transition_reopen_and_close(db_session):
    """Verifies reopening a resolved alert and subsequently closing it."""
    alert = create_base_alert(db_session, status=AlertStatus.RESOLVED.value)

    reopened = transition_alert_status(
        db=db_session,
        alert_instance_id=alert.id,
        action="REOPEN",
        actor="auditor@company.com",
        notes="Cost spike recurred in subsequent billing window.",
    )
    assert reopened.status == AlertStatus.OPEN.value

    closed = transition_alert_status(
        db=db_session,
        alert_instance_id=alert.id,
        action="CLOSE",
        actor="finops-lead@company.com",
        notes="Issue completely remediated after architecture review.",
    )
    assert closed.status == AlertStatus.CLOSED.value

    # Verify history chain has 2 events
    history = (
        db_session.query(AlertHistory)
        .filter(AlertHistory.alert_instance_id == alert.id)
        .all()
    )
    assert len(history) == 2
    actions = [h.action for h in history]
    assert "REOPEN" in actions
    assert "CLOSE" in actions
