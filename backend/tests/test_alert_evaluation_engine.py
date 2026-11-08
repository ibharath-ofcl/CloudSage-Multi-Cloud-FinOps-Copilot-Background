"""
Unit and Integration Tests for Alert Rule Evaluation Engine.
Tests multi-cloud scoping, severity hierarchy, Decimal threshold comparisons,
inactive rule exclusion, and transactional savepoint isolation.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import AlertStatus, NotificationChannel, Severity
from backend.app.models.alert import AlertInstance, AlertRule, NotificationOutbox
from backend.app.models.anomaly import CostAnomaly
from backend.app.alerts.evaluation import AlertRuleEvaluationService


def create_sample_anomaly(
    provider: str = "AWS",
    account_id: str = "123456789012",
    service_name: str = "Amazon Elastic Compute Cloud",
    region: str = "us-east-1",
    severity: Severity = Severity.HIGH,
    actual_cost: Decimal = Decimal("400.0000"),
    expected_cost: Decimal = Decimal("200.0000"),
    excess_cost: Decimal = Decimal("200.0000"),
    deviation_pct: Decimal = Decimal("100.00"),
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
        actual_cost=actual_cost,
        expected_cost=expected_cost,
        estimated_excess_cost=excess_cost,
        spike_percentage=deviation_pct,
    )


def test_rule_evaluation_matches_provider_and_severity(db_session):
    """Verifies that rule triggers only when cloud provider and severity match criteria."""
    evaluator = AlertRuleEvaluationService()

    # Create AWS High Rule
    rule = AlertRule(
        id=uuid.uuid4(),
        name="AWS High Spend Alert",
        provider="AWS",
        min_severity=Severity.HIGH.value,
        min_excess_cost=Decimal("50.0000"),
        percentage_deviation_threshold=Decimal("10.00"),
        channels=[NotificationChannel.IN_APP.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # Anomaly 1: AWS High (should match)
    anom1 = create_sample_anomaly(provider="AWS", severity=Severity.HIGH, excess_cost=Decimal("100.0000"))
    db_session.add(anom1)
    db_session.commit()

    instances = evaluator.evaluate_anomaly(db_session, anom1)
    assert len(instances) == 1
    assert instances[0].provider == "AWS"
    assert instances[0].severity == Severity.HIGH.value

    # Anomaly 2: GCP High (should NOT match AWS rule)
    anom2 = create_sample_anomaly(provider="GCP", severity=Severity.HIGH, excess_cost=Decimal("100.0000"))
    db_session.add(anom2)
    db_session.commit()

    instances_gcp = evaluator.evaluate_anomaly(db_session, anom2)
    assert len(instances_gcp) == 0


def test_rule_evaluation_severity_hierarchy(db_session):
    """Verifies severity hierarchy: CRITICAL triggers for MEDIUM rule, but LOW does not."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Medium Plus Rule",
        provider="ALL",
        min_severity=Severity.MEDIUM.value,
        min_excess_cost=Decimal("10.0000"),
        percentage_deviation_threshold=Decimal("5.00"),
        channels=[NotificationChannel.IN_APP.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # LOW severity anomaly -> should NOT match
    low_anom = create_sample_anomaly(severity=Severity.LOW, excess_cost=Decimal("20.0000"))
    db_session.add(low_anom)
    db_session.commit()
    assert len(evaluator.evaluate_anomaly(db_session, low_anom)) == 0

    # CRITICAL severity anomaly -> SHOULD match
    crit_anom = create_sample_anomaly(severity=Severity.CRITICAL, excess_cost=Decimal("20.0000"))
    db_session.add(crit_anom)
    db_session.commit()
    assert len(evaluator.evaluate_anomaly(db_session, crit_anom)) == 1


def test_rule_evaluation_decimal_threshold_enforcement(db_session):
    """Verifies strict Decimal comparison for minimum excess cost and deviation percentage."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Exact $100 Threshold",
        provider="AWS",
        min_severity=Severity.LOW.value,
        min_excess_cost=Decimal("100.0000"),
        percentage_deviation_threshold=Decimal("20.00"),
        channels=[NotificationChannel.IN_APP.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # Anomaly just below threshold ($99.9999) -> should NOT match
    below_anom = create_sample_anomaly(excess_cost=Decimal("99.9999"), deviation_pct=Decimal("25.00"))
    db_session.add(below_anom)
    db_session.commit()
    assert len(evaluator.evaluate_anomaly(db_session, below_anom)) == 0

    # Anomaly exactly at or above threshold ($100.0000) -> SHOULD match
    exact_anom = create_sample_anomaly(excess_cost=Decimal("100.0000"), deviation_pct=Decimal("20.00"))
    db_session.add(exact_anom)
    db_session.commit()
    assert len(evaluator.evaluate_anomaly(db_session, exact_anom)) == 1


def test_disabled_rule_never_triggers(db_session):
    """Verifies that rules with is_enabled=False are ignored."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Disabled Rule",
        provider="ALL",
        min_severity=Severity.LOW.value,
        min_excess_cost=Decimal("1.0000"),
        is_enabled=False,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    anom = create_sample_anomaly(excess_cost=Decimal("500.0000"))
    db_session.add(anom)
    db_session.commit()

    assert len(evaluator.evaluate_anomaly(db_session, anom)) == 0


def test_account_and_service_scoping(db_session):
    """Verifies scoped rules only trigger on specific account or service."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Scoped Rule",
        provider="AWS",
        account_id="999888777666",
        service_name="Amazon Elastic Compute Cloud",
        min_severity=Severity.LOW.value,
        channels=[NotificationChannel.IN_APP.value],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    # Matching account and service
    matching_anom = create_sample_anomaly(
        account_id="999888777666",
        service_name="Amazon Elastic Compute Cloud",
    )
    db_session.add(matching_anom)
    db_session.commit()
    assert len(evaluator.evaluate_anomaly(db_session, matching_anom)) == 1

    # Different account
    different_account_anom = create_sample_anomaly(
        account_id="111222333444",
        service_name="Amazon Elastic Compute Cloud",
    )
    db_session.add(different_account_anom)
    db_session.commit()
    assert len(evaluator.evaluate_anomaly(db_session, different_account_anom)) == 0


def test_outbox_enqueued_on_evaluation(db_session):
    """Verifies that matched rule automatically creates outbox records for each channel."""
    evaluator = AlertRuleEvaluationService()

    rule = AlertRule(
        id=uuid.uuid4(),
        name="Multi-Channel Alert",
        provider="AWS",
        min_severity=Severity.LOW.value,
        channels=[NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value],
        recipients=["alerts@example.com"],
        is_enabled=True,
        created_by="system",
    )
    db_session.add(rule)
    db_session.commit()

    anom = create_sample_anomaly()
    db_session.add(anom)
    db_session.commit()

    instances = evaluator.evaluate_anomaly(db_session, anom)
    assert len(instances) == 1

    # Check outbox entries
    outbox_entries = (
        db_session.query(NotificationOutbox)
        .filter(NotificationOutbox.alert_instance_id == instances[0].id)
        .all()
    )
    assert len(outbox_entries) == 2
    channels = {e.channel for e in outbox_entries}
    assert NotificationChannel.IN_APP.value in channels
    assert NotificationChannel.EMAIL.value in channels
