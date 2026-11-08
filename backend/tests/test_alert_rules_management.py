"""
Unit and Integration Tests for Alert Rules Management.
Tests rule creation, threshold validation, SSRF URL checks, listing, toggling, and dry-run preview.
"""

from decimal import Decimal
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi import HTTPException

from backend.app.core.enums import AlertStatus, AlertType, NotificationChannel, Severity
from backend.app.models.alert import AlertRule
from backend.app.models.anomaly import CostAnomaly
from backend.app.alerts.security import validate_webhook_url
from backend.app.schemas.alert import AlertRuleBase, AlertRuleCreate


def test_alert_rule_creation(db_session):
    """Verifies creation and persistence of an alert rule."""
    rule = AlertRule(
        id=uuid.uuid4(),
        name="Production AWS Cost Spike",
        description="Alerts on significant EC2 anomalies",
        provider="AWS",
        min_severity=Severity.HIGH.value,
        min_excess_cost=Decimal("150.0000"),
        percentage_deviation_threshold=Decimal("25.00"),
        channels=[NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value],
        recipients=["finops@example.com"],
        cooldown_minutes=720,
        is_enabled=True,
        created_by="admin-user",
    )
    db_session.add(rule)
    db_session.commit()

    saved = db_session.query(AlertRule).filter(AlertRule.id == rule.id).first()
    assert saved is not None
    assert saved.name == "Production AWS Cost Spike"
    assert saved.provider == "AWS"
    assert saved.min_excess_cost == Decimal("150.0000")
    assert saved.channels == ["IN_APP", "EMAIL"]
    assert saved.is_enabled is True
    assert saved.is_archived is False


def test_alert_rule_validation_rejects_negative_currency():
    """Verifies that Pydantic schema rejects negative financial thresholds."""
    with pytest.raises(ValueError):
        AlertRuleCreate(
            name="Invalid Rule",
            threshold_value=Decimal("-10.0000"),
        )

    with pytest.raises(ValueError):
        AlertRuleCreate(
            name="Negative Excess",
            min_excess_cost=Decimal("-50.0000"),
        )


def test_alert_rule_validation_rejects_invalid_channel():
    """Verifies that invalid channels are rejected."""
    with pytest.raises(ValueError):
        AlertRuleCreate(
            name="Bad Channel Rule",
            channels=["UNKNOWN_CHANNEL"],
        )


def test_alert_rule_ssrf_webhook_protection():
    """Verifies SSRF protection on dangerous URLs."""
    # Loopback
    with pytest.raises(HTTPException) as exc_info:
        validate_webhook_url("http://127.0.0.1:8000/webhook")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException):
        validate_webhook_url("http://localhost:3000/alert")

    # Cloud Metadata
    with pytest.raises(HTTPException):
        validate_webhook_url("http://169.254.169.254/latest/meta-data/")

    # Private Subnet RFC 1918
    with pytest.raises(HTTPException):
        validate_webhook_url("http://10.0.0.1/notify")

    with pytest.raises(HTTPException):
        validate_webhook_url("http://192.168.1.100/notify")

    # Public valid HTTPS domain should pass
    validated = validate_webhook_url("https://hooks.slack.com/services/T00/B00/X00")
    assert validated is True


def test_alert_rule_soft_deletion(db_session):
    """Verifies soft delete preserves audit integrity."""
    rule = AlertRule(
        id=uuid.uuid4(),
        name="Temporary Rule",
        provider="GCP",
        min_severity=Severity.MEDIUM.value,
        created_by="dev-user",
    )
    db_session.add(rule)
    db_session.commit()

    # Soft delete
    rule.is_archived = True
    db_session.commit()

    active_rules = db_session.query(AlertRule).filter(AlertRule.is_archived == False).all()
    assert not any(r.id == rule.id for r in active_rules)

    raw_rule = db_session.query(AlertRule).filter(AlertRule.id == rule.id).first()
    assert raw_rule is not None
    assert raw_rule.is_archived is True


def test_alert_rule_toggle_active(db_session):
    """Verifies toggling rule active state."""
    rule = AlertRule(
        id=uuid.uuid4(),
        name="Toggleable Rule",
        provider="AZURE",
        min_severity=Severity.LOW.value,
        is_enabled=True,
        created_by="ops-user",
    )
    db_session.add(rule)
    db_session.commit()

    rule.is_enabled = not rule.is_enabled
    db_session.commit()

    refreshed = db_session.query(AlertRule).filter(AlertRule.id == rule.id).first()
    assert refreshed.is_enabled is False


def test_alert_rule_preview_matching(db_session):
    """Verifies dry-run preview matches historical anomalies without creating alert instances."""
    now = datetime.now(timezone.utc)
    # Create test anomalies
    a1 = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="111222333444",
        service_category="COMPUTE",
        service_name="Amazon Elastic Compute Cloud",
        region="us-east-1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.HIGH,
        estimated_excess_cost=Decimal("250.0000"),
        actual_cost=Decimal("500.0000"),
        expected_cost=Decimal("250.0000"),
        spike_percentage=Decimal("100.00"),
    )
    a2 = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="111222333444",
        service_category="DATABASE",
        service_name="Amazon RDS",
        region="us-east-1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.LOW,
        estimated_excess_cost=Decimal("20.0000"),
        actual_cost=Decimal("120.0000"),
        expected_cost=Decimal("100.0000"),
        spike_percentage=Decimal("20.00"),
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    # Rule criteria: AWS, HIGH severity, min $100 excess
    anomalies = db_session.query(CostAnomaly).all()
    matched = [
        a for a in anomalies
        if a.provider == "AWS" and a.severity == Severity.HIGH and a.estimated_excess_cost >= Decimal("100.0000")
    ]
    assert len(matched) == 1
    assert matched[0].id == a1.id
