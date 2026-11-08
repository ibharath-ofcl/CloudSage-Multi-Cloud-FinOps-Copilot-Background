"""
Unit and Integration Tests for Alert Deduplication, Cooldown, and Escalation.
Tests dedup key generation, suppression during cooldown, cooldown window expiry,
and severity escalation bypassing cooldown.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import AlertStatus, NotificationChannel, Severity
from backend.app.models.alert import AlertInstance, AlertRule, NotificationOutbox
from backend.app.models.anomaly import CostAnomaly
from backend.app.alerts.evaluation import AlertRuleEvaluationService


def create_anomaly(
    provider="AWS",
    account_id="111222333444",
    service_name="Amazon EC2",
    region="us-east-1",
    severity=Severity.MEDIUM,
    excess_cost=Decimal("150.0000"),
    deviation_pct=Decimal("50.00"),
) -> CostAnomaly:
    now = datetime.now(timezone.utc)
    return CostAnomaly(
        id=uuid.uuid4(),
        provider=provider,
        account_id=account_id,
        service_category="COMPUTE",
        service_name=service_name,
        region=region,
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=severity,
        actual_cost=excess_cost * Decimal("2"),
        expected_cost=excess_cost,
        estimated_excess_cost=excess_cost,
        spike_percentage=deviation_pct,
    )


def test_dedup_key_deterministic_generation(db_session):
    """Verifies that dedup key is deterministic across identical dimensions."""
    evaluator = AlertRuleEvaluationService()

    rule_id = uuid.uuid4()
    key1 = evaluator.generate_dedup_key("AWS", "123", "EC2", "us-east-1", "i-123", rule_id)
    key2 = evaluator.generate_dedup_key("AWS", "123", "EC2", "us-east-1", "i-123", rule_id)
    assert key1 == key2
    assert "AWS" in key1
    assert "123" in key1

    # Changing resource ID changes dedup key
    key3 = evaluator.generate_dedup_key("AWS", "123", "EC2", "us-east-1", "i-456", rule_id)
    assert key1 != key3


def test_cooldown_suppression_increments_trigger_count(db_session):
    """Verifies that an alert inside its cooldown window is suppressed and increments trigger count."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="EC2 Alert with 24h Cooldown",
        provider="AWS",
        min_severity=Severity.LOW.value,
        cooldown_minutes=1440,  # 24 hours
        channels=[NotificationChannel.IN_APP.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # Initial trigger
    anom1 = create_anomaly()
    db_session.add(anom1)
    db_session.commit()

    instances1 = evaluator.evaluate_anomaly(db_session, anom1)
    assert len(instances1) == 1
    inst = instances1[0]
    assert inst.status == AlertStatus.OPEN.value
    assert inst.trigger_count == 1

    # Immediate second trigger with same anomaly/dimensions
    anom2 = create_anomaly()
    db_session.add(anom2)
    db_session.commit()

    instances2 = evaluator.evaluate_anomaly(db_session, anom2)
    assert len(instances2) == 1
    updated_inst = instances2[0]
    assert updated_inst.id == inst.id
    assert updated_inst.trigger_count == 2
    # Status remains unchanged or suppressed
    assert updated_inst.status in (AlertStatus.OPEN.value, AlertStatus.SUPPRESSED.value)


def test_cooldown_expiry_allows_new_notifications(db_session):
    """Verifies that after cooldown window expires, a new notification is triggered."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Short Cooldown Rule",
        provider="AWS",
        min_severity=Severity.LOW.value,
        cooldown_minutes=60,
        channels=[NotificationChannel.IN_APP.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # Create previous alert instance that expired 2 hours ago
    expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
    existing_instance = AlertInstance(
        id=uuid.uuid4(),
        alert_rule_id=rule.id,
        anomaly_id=uuid.uuid4(),
        dedup_key=evaluator.generate_dedup_key("AWS", "111222333444", "Amazon EC2", "us-east-1", None, rule.id),
        title="Existing EC2 Alert",
        severity=Severity.MEDIUM.value,
        status=AlertStatus.RESOLVED.value,
        provider="AWS",
        account_id="111222333444",
        service_name="Amazon EC2",
        region="us-east-1",
        first_triggered_at=expired_time - timedelta(days=1),
        last_triggered_at=expired_time,
        suppress_until=expired_time,  # Already expired
        trigger_count=1,
    )
    db_session.add(existing_instance)
    db_session.commit()

    # New anomaly arrives now
    new_anom = create_anomaly()
    db_session.add(new_anom)
    db_session.commit()

    result = evaluator.evaluate_anomaly(db_session, new_anom)
    assert len(result) == 1
    refreshed = result[0]
    # Cooldown was expired, so alert is reopened to OPEN
    assert refreshed.status == AlertStatus.OPEN.value
    assert refreshed.trigger_count == 2


def test_severity_escalation_bypasses_cooldown(db_session):
    """Verifies that an increase in anomaly severity (e.g. MEDIUM to CRITICAL) escalates and notifies."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Escalation Rule",
        provider="AWS",
        min_severity=Severity.LOW.value,
        cooldown_minutes=1440,
        channels=[NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # Initial trigger at MEDIUM severity
    anom_medium = create_anomaly(severity=Severity.MEDIUM, excess_cost=Decimal("100.0000"))
    db_session.add(anom_medium)
    db_session.commit()

    evaluator.evaluate_anomaly(db_session, anom_medium)

    initial_outbox_count = db_session.query(NotificationOutbox).count()
    assert initial_outbox_count == 2  # IN_APP and EMAIL

    # Subsequent trigger at CRITICAL severity with 4x spend
    anom_crit = create_anomaly(severity=Severity.CRITICAL, excess_cost=Decimal("500.0000"))
    db_session.add(anom_crit)
    db_session.commit()

    res = evaluator.evaluate_anomaly(db_session, anom_crit)
    assert len(res) == 1
    escalated = res[0]
    assert escalated.severity == Severity.CRITICAL.value
    assert escalated.escalation_level >= 1

    # Escalation generated new outbox records despite cooldown
    new_outbox_count = db_session.query(NotificationOutbox).count()
    assert new_outbox_count > initial_outbox_count
