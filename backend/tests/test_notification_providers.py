"""
Unit and Integration Tests for Notification Delivery Providers.
Tests In-App, Email (HTML template rendering & advisory disclaimer & mock capture),
Webhook (with SSRF protection), Slack, and Teams providers.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
import uuid
import pytest

from backend.app.core.config import settings
from backend.app.models.alert import InAppNotification
from backend.app.alerts.providers import (
    EmailNotificationProvider,
    InAppNotificationProvider,
    SlackNotificationProvider,
    TeamsNotificationProvider,
    WebhookNotificationProvider,
)


def test_in_app_provider_dispatch(db_session):
    """Verifies In-App provider dispatch contract and database model persistence."""
    provider = InAppNotificationProvider()

    payload = {
        "alert_instance_id": str(uuid.uuid4()),
        "title": "AWS RDS Cost Spike",
        "provider": "AWS",
        "account_id": "123456789012",
        "service_name": "Amazon Relational Database Service",
        "severity": "HIGH",
        "excess_cost": "350.00",
        "explanation": "Multi-AZ replica provisioned causing unexpected surge",
    }

    success, code, body, err = provider.dispatch(
        recipient="user-finops-1",
        subject="High Cost Alert: AWS RDS",
        payload=payload,
    )

    assert success is True
    assert code in (200, 250)

    notif = InAppNotification(
        id=uuid.uuid4(),
        recipient_user_id="user-finops-1",
        title=payload["title"],
        message=payload["explanation"],
        severity=payload["severity"],
        provider=payload["provider"],
        account_id=payload["account_id"],
        service_name=payload["service_name"],
        excess_cost=Decimal(payload["excess_cost"]),
    )
    db_session.add(notif)
    db_session.commit()

    saved = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.recipient_user_id == "user-finops-1")
        .first()
    )
    assert saved is not None
    assert saved.title == "AWS RDS Cost Spike"
    assert saved.provider == "AWS"
    assert saved.severity == "HIGH"
    assert saved.is_read is False


def test_email_provider_html_rendering_and_advisory_disclaimer():
    """Verifies email template includes the mandatory non-destructive advisory disclaimer."""
    provider = EmailNotificationProvider()

    payload = {
        "alert_instance_id": str(uuid.uuid4()),
        "title": "GCP BigQuery Spike",
        "provider": "GCP",
        "account_id": "gcp-prod-analytics",
        "service_name": "BigQuery",
        "severity": "CRITICAL",
        "current_cost": "1200.00",
        "expected_cost": "200.00",
        "excess_cost": "1000.00",
        "percentage_deviation": "500.0",
        "explanation": "Unpartitioned query on 50TB dataset.",
    }

    html = provider.render_email_html("CRITICAL Alert: BigQuery Surge", payload)

    # Must contain financial details
    assert "$1000.00" in html or "$1,000.00" in html or "1000.00" in html
    assert "BigQuery" in html
    assert "GCP" in html

    # Mandatory advisory safety disclaimer
    assert "advisory" in html.lower()
    assert "no cloud" in html.lower() or "strictly advisory" in html.lower()


def test_email_provider_safe_mock_capture():
    """Verifies email provider in safe dev mode captures messages in memory without external SMTP."""
    EmailNotificationProvider.clear_captured_emails()
    provider = EmailNotificationProvider()

    payload = {
        "title": "Staging Anomaly",
        "provider": "AZURE",
        "service_name": "Azure App Services",
        "severity": "MEDIUM",
        "excess_cost": "75.00",
    }

    success, code, body, err = provider.dispatch(
        recipient="test-engineer@company.com",
        subject="Staging Azure Spike",
        payload=payload,
    )

    assert success is True
    assert code in (200, 250)
    captured = EmailNotificationProvider.captured_emails
    assert len(captured) >= 1
    assert captured[-1]["recipient"] == "test-engineer@company.com"
    assert "Staging Azure Spike" in captured[-1]["subject"]


def test_webhook_provider_ssrf_rejection():
    """Verifies that webhook provider blocks SSRF attacks and returns failure without sending."""
    provider = WebhookNotificationProvider(allow_test_destinations=False)

    payload = {"data": "test"}

    # AWS/GCP/Azure Metadata IP
    success, code, body, err = provider.dispatch(
        recipient="http://169.254.169.254/latest/meta-data/",
        subject="Test",
        payload=payload,
    )
    assert success is False
    assert code == 400
    assert "SSRF" in err or "forbidden" in err.lower() or "metadata" in err.lower()

    # Localhost loopback
    success, code, body, err = provider.dispatch(
        recipient="http://127.0.0.1:9000/internal",
        subject="Test",
        payload=payload,
    )
    assert success is False
    assert code == 400


def test_webhook_provider_mock_capture():
    """Verifies mock webhook capture for safe test endpoints."""
    WebhookNotificationProvider.clear_captured_webhooks()
    provider = WebhookNotificationProvider(allow_test_destinations=True)

    payload = {
        "alert_instance_id": str(uuid.uuid4()),
        "title": "Mock Webhook Trigger",
    }

    success, code, body, err = provider.dispatch(
        recipient="test://webhook-collector",
        subject="Test Webhook Alert",
        payload=payload,
    )

    assert success is True
    assert code in (200, 250)
    assert len(WebhookNotificationProvider.captured_webhooks) == 1
    assert WebhookNotificationProvider.captured_webhooks[0]["recipient"] == "test://webhook-collector"


def test_slack_and_teams_providers_structure():
    """Verifies Slack and Teams providers format structured payloads."""
    slack_provider = SlackNotificationProvider(allow_test_destinations=True)
    teams_provider = TeamsNotificationProvider(allow_test_destinations=True)

    payload = {
        "alert_instance_id": str(uuid.uuid4()),
        "title": "EC2 Sudden Increase",
        "provider": "AWS",
        "service_name": "Amazon EC2",
        "severity": "CRITICAL",
        "excess_cost": "450.00",
    }

    s_ok, s_code, _, _ = slack_provider.dispatch(
        recipient="test://slack-channel",
        subject="Slack Alert",
        payload=payload,
    )
    assert s_ok is True

    t_ok, t_code, _, _ = teams_provider.dispatch(
        recipient="test://teams-webhook",
        subject="Teams Alert",
        payload=payload,
    )
    assert t_ok is True
