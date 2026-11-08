"""
Integration Tests for Alerting & Enterprise Notification Hub REST API Endpoints.
Verifies all endpoints across:
1. /api/v1/alert-rules (CRUD, preview, toggle)
2. /api/v1/alerts (Listing, stats, detail, lifecycle action, history)
3. /api/v1/notifications (Inbox, unread counter, read/unread, mark all read)
4. /api/v1/notification-deliveries (Outbox, health, retry, cancel)
5. /api/v1/notification-preferences (Get/update preferences)
6. Authenticated principal resolution and role verification
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import AlertStatus, NotificationChannel, NotificationDeliveryStatus, Severity, UserRole
from backend.app.main import app
from backend.app.models.alert import (
    AlertHistory,
    AlertInstance,
    AlertRule,
    InAppNotification,
    NotificationOutbox,
    NotificationPreference,
)
from backend.app.models.anomaly import CostAnomaly


@pytest.fixture
def client(engine):
    """Yield TestClient with overridden database session and thread-safe engine."""
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_sync_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_api_create_and_list_alert_rules(client):
    """Verifies creating an alert rule via API and listing rules."""
    headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@cloudsage.com"}
    create_payload = {
        "name": "Production EC2 Spike Rule",
        "description": "Monitors surge in AWS EC2 compute",
        "provider": "AWS",
        "min_severity": "HIGH",
        "min_excess_cost": 150.0,
        "percentage_deviation_threshold": 30.0,
        "cooldown_minutes": 1440,
        "channels": ["IN_APP", "EMAIL"],
        "recipients": ["finops-oncall@cloudsage.com"],
        "is_enabled": True,
    }

    res = client.post("/api/v1/alert-rules", json=create_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Production EC2 Spike Rule"
    assert data["provider"] == "AWS"
    assert data["is_enabled"] is True
    rule_id = data["id"]

    # List rules
    list_res = client.get("/api/v1/alert-rules", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == rule_id for r in list_data["items"])


def test_api_get_update_toggle_delete_alert_rule(client):
    """Verifies detail, update, toggle active, and soft delete of an alert rule."""
    headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@cloudsage.com"}
    create_res = client.post(
        "/api/v1/alert-rules",
        json={"name": "Rule To Manage", "provider": "GCP", "min_severity": "MEDIUM"},
        headers=headers,
    )
    rule_id = create_res.json()["id"]

    # Get Rule
    get_res = client.get(f"/api/v1/alert-rules/{rule_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Rule To Manage"

    # Update Rule
    update_res = client.put(
        f"/api/v1/alert-rules/{rule_id}",
        json={"name": "Updated Rule Name", "min_excess_cost": 200.0},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Rule Name"

    # Toggle Rule
    toggle_res = client.post(f"/api/v1/alert-rules/{rule_id}/toggle", headers=headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_enabled"] is False

    # Delete Rule (Soft Delete)
    del_res = client.delete(f"/api/v1/alert-rules/{rule_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 404 after deletion
    get_after_del = client.get(f"/api/v1/alert-rules/{rule_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_api_preview_alert_rule(client, engine):
    """Verifies dry-run rule preview endpoint against historical anomalies."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)
    anom = CostAnomaly(
        id=uuid.uuid4(),
        provider="AZURE",
        account_id="sub-corp-prod",
        service_category="COMPUTE",
        service_name="Virtual Machines",
        region="eastus",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.HIGH,
        actual_cost=Decimal("800.0000"),
        expected_cost=Decimal("400.0000"),
        estimated_excess_cost=Decimal("400.0000"),
        spike_percentage=Decimal("100.00"),
    )
    session.add(anom)
    session.commit()
    session.close()

    preview_payload = {
        "provider": "AZURE",
        "min_severity": "MEDIUM",
        "min_excess_cost": 100.0,
        "percentage_deviation_threshold": 50.0,
    }
    res = client.post("/api/v1/alert-rules/preview", json=preview_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["matched_count"] >= 1
    assert data["sample_matches"][0]["service_name"] == "Virtual Machines"


def test_api_list_alerts_and_stats(client, engine):
    """Verifies listing materialized alerts and aggregated stats."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    anom = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="111222333444",
        service_category="STORAGE",
        service_name="Amazon S3",
        region="us-east-1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.HIGH,
        actual_cost=Decimal("200.0000"),
        expected_cost=Decimal("100.0000"),
        estimated_excess_cost=Decimal("100.0000"),
        spike_percentage=Decimal("100.00"),
    )
    session.add(anom)
    session.flush()

    alert = AlertInstance(
        id=uuid.uuid4(),
        anomaly_id=anom.id,
        dedup_key="acct:AWS:111:S3:us-east-1:1",
        title="S3 Bucket Cost Spike",
        severity=Severity.HIGH.value,
        status=AlertStatus.OPEN.value,
        provider="AWS",
        account_id="111222333444",
        service_name="Amazon S3",
        region="us-east-1",
        current_cost=Decimal("200.0000"),
        expected_cost=Decimal("100.0000"),
        excess_cost=Decimal("100.0000"),
        percentage_deviation=Decimal("100.00"),
        first_triggered_at=now,
        last_triggered_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    session.commit()
    session.close()

    # GET /alerts
    alerts_res = client.get("/api/v1/alerts")
    assert alerts_res.status_code == 200
    assert alerts_res.json()["total"] >= 1

    # GET /alerts/stats
    stats_res = client.get("/api/v1/alerts/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_alerts"] >= 1
    assert stats["high_alerts"] >= 1
    assert stats["unacknowledged_alerts"] >= 1


def test_api_get_alert_detail_and_history(client, engine):
    """Verifies retrieving alert detail with linked anomaly and history."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    anom = CostAnomaly(
        id=uuid.uuid4(),
        provider="GCP",
        account_id="gcp-analytics",
        service_category="ANALYTICS",
        service_name="BigQuery",
        region="us-central1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.CRITICAL,
        actual_cost=Decimal("1000.0000"),
        expected_cost=Decimal("200.0000"),
        estimated_excess_cost=Decimal("800.0000"),
        spike_percentage=Decimal("400.00"),
    )
    session.add(anom)
    session.flush()

    alert = AlertInstance(
        id=uuid.uuid4(),
        anomaly_id=anom.id,
        dedup_key="acct:GCP:analytics:BigQuery:us-central1:1",
        title="BigQuery Critical Spike",
        severity=Severity.CRITICAL.value,
        status=AlertStatus.OPEN.value,
        provider="GCP",
        account_id="gcp-analytics",
        service_name="BigQuery",
        region="us-central1",
        current_cost=Decimal("1000.0000"),
        expected_cost=Decimal("200.0000"),
        excess_cost=Decimal("800.0000"),
        percentage_deviation=Decimal("400.00"),
        first_triggered_at=now,
        last_triggered_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    session.commit()
    alert_id = str(alert.id)
    session.close()

    res = client.get(f"/api/v1/alerts/{alert_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "BigQuery Critical Spike"
    assert data["severity"] == "CRITICAL"
    assert data["anomaly"] is not None
    assert data["anomaly"]["service_name"] is not None or "anomaly_category" in data["anomaly"]


def test_api_alert_lifecycle_action_acknowledge_and_investigate(client, engine):
    """Verifies executing ACKNOWLEDGE and INVESTIGATE actions."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    anom = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="111222333444",
        service_category="COMPUTE",
        service_name="Amazon EC2",
        region="us-east-1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.HIGH,
        actual_cost=Decimal("500.0000"),
        expected_cost=Decimal("250.0000"),
        estimated_excess_cost=Decimal("250.0000"),
        spike_percentage=Decimal("100.00"),
    )
    session.add(anom)
    session.flush()

    alert = AlertInstance(
        id=uuid.uuid4(),
        anomaly_id=anom.id,
        dedup_key="acct:AWS:ec2:triage:1",
        title="EC2 Surge for Action",
        severity=Severity.HIGH.value,
        status=AlertStatus.OPEN.value,
        provider="AWS",
        account_id="111222333444",
        service_name="Amazon EC2",
        region="us-east-1",
        current_cost=Decimal("500.0000"),
        expected_cost=Decimal("250.0000"),
        excess_cost=Decimal("250.0000"),
        percentage_deviation=Decimal("100.00"),
        first_triggered_at=now,
        last_triggered_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    session.commit()
    alert_id = str(alert.id)
    session.close()

    headers = {"X-User-Role": "FINOPS_ADMIN", "X-User-Email": "triage@cloudsage.com"}

    # Action: ACKNOWLEDGE
    ack_res = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "ACKNOWLEDGE", "ticket_ref": "FIN-4092"},
        headers=headers,
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == AlertStatus.ACKNOWLEDGED.value

    # Action: INVESTIGATE
    inv_res = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "INVESTIGATE", "notes": "Checking spot instance terminations"},
        headers=headers,
    )
    assert inv_res.status_code == 200
    assert inv_res.json()["status"] == AlertStatus.INVESTIGATING.value


def test_api_alert_lifecycle_action_resolve_requires_notes(client, engine):
    """Verifies that resolving an alert requires mandatory resolution notes."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    anom = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="111222333444",
        service_category="COMPUTE",
        service_name="Amazon EC2",
        region="us-east-1",
        anomaly_date=now.date(),
        detected_at=now,
        first_detected_at=now,
        last_detected_at=now,
        severity=Severity.HIGH,
        actual_cost=Decimal("500.0000"),
        expected_cost=Decimal("250.0000"),
        estimated_excess_cost=Decimal("250.0000"),
        spike_percentage=Decimal("100.00"),
    )
    session.add(anom)
    session.flush()

    alert = AlertInstance(
        id=uuid.uuid4(),
        anomaly_id=anom.id,
        dedup_key="acct:AWS:ec2:resolve:1",
        title="Resolve Me Alert",
        severity=Severity.HIGH.value,
        status=AlertStatus.INVESTIGATING.value,
        provider="AWS",
        account_id="111222333444",
        service_name="Amazon EC2",
        region="us-east-1",
        current_cost=Decimal("300.0000"),
        expected_cost=Decimal("150.0000"),
        excess_cost=Decimal("150.0000"),
        percentage_deviation=Decimal("100.00"),
        first_triggered_at=now,
        last_triggered_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    session.commit()
    alert_id = str(alert.id)
    session.close()

    headers = {"X-User-Role": "FINOPS_ADMIN", "X-User-Email": "lead@cloudsage.com"}

    # Resolve without notes -> 400 Bad Request
    fail_res = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "RESOLVE"},
        headers=headers,
    )
    assert fail_res.status_code == 400

    # Resolve with notes -> 200 OK
    ok_res = client.post(
        f"/api/v1/alerts/{alert_id}/action",
        json={"action": "RESOLVE", "notes": "Cleaned up orphaned EBS volumes and snapshots."},
        headers=headers,
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == AlertStatus.RESOLVED.value


def test_api_in_app_notifications_lifecycle(client, engine):
    """Verifies listing, unread-count, marking read/unread, and mark-all-read."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    user_email = "test-user@cloudsage.com"
    notif = InAppNotification(
        id=uuid.uuid4(),
        recipient_user_id=user_email,
        title="Test In-App Notification",
        message="Notice of cost spike",
        severity="HIGH",
        provider="AWS",
        account_id="123",
        service_name="EC2",
        excess_cost=Decimal("50.0000"),
        is_read=False,
        created_at=now,
    )
    session.add(notif)
    session.commit()
    notif_id = str(notif.id)
    session.close()

    headers = {"X-User-Email": user_email}

    # 1. Check unread count
    cnt_res = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert cnt_res.status_code == 200
    assert cnt_res.json()["unread_count"] >= 1

    # 2. List notifications
    list_res = client.get("/api/v1/notifications", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Mark read
    read_res = client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # 4. Mark unread
    unread_res = client.post(f"/api/v1/notifications/{notif_id}/unread", headers=headers)
    assert unread_res.status_code == 200
    assert unread_res.json()["is_read"] is False

    # 5. Mark all read
    mark_all_res = client.post("/api/v1/notifications/mark-all-read", headers=headers)
    assert mark_all_res.status_code == 200
    assert mark_all_res.json()["marked_read_count"] >= 1


def test_api_notification_outbox_listing_and_health(client, engine):
    """Verifies listing outbox items and querying pipeline health."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.EMAIL.value,
        recipient="eng@cloudsage.com",
        subject="Pipeline Health Check",
        payload={"data": "test"},
        status=NotificationDeliveryStatus.PENDING,
        attempts=0,
        max_attempts=5,
        created_at=now,
    )
    session.add(item)
    session.commit()
    session.close()

    # List outbox
    outbox_res = client.get("/api/v1/notification-deliveries/outbox")
    assert outbox_res.status_code == 200
    assert outbox_res.json()["total"] >= 1

    # Health check
    health_res = client.get("/api/v1/notification-deliveries/health")
    assert health_res.status_code == 200
    health = health_res.json()
    assert health["status"] in ("HEALTHY", "DEGRADED")
    assert health["pending_outbox_count"] >= 1


def test_api_outbox_retry_and_cancel(client, engine):
    """Verifies manual retry and cancel on outbox items."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    now = datetime.now(timezone.utc)

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.WEBHOOK.value,
        recipient="https://api.test.com/dlq",
        subject="Dead Lettered Notice",
        payload={"data": "test"},
        status=NotificationDeliveryStatus.DEAD_LETTERED,
        attempts=5,
        max_attempts=5,
        created_at=now,
    )
    session.add(item)
    session.commit()
    outbox_id = str(item.id)
    session.close()

    headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@cloudsage.com"}

    # Retry
    retry_res = client.post(f"/api/v1/notification-deliveries/outbox/{outbox_id}/retry", headers=headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["new_status"] == NotificationDeliveryStatus.PENDING.value

    # Cancel
    cancel_res = client.post(f"/api/v1/notification-deliveries/outbox/{outbox_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == NotificationDeliveryStatus.CANCELLED.value


def test_api_user_notification_preferences(client):
    """Verifies retrieving and updating user notification preferences."""
    headers = {"X-User-Email": "preferences-user@cloudsage.com"}

    # GET preferences
    get_res = client.get("/api/v1/notification-preferences/me", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["user_email"] == "preferences-user@cloudsage.com"

    # PUT preferences
    update_payload = {
        "enabled_channels": ["IN_APP"],
        "min_severity": "CRITICAL",
        "receive_digests": True,
        "digest_frequency": "WEEKLY",
        "quiet_hours_enabled": True,
        "quiet_hours_start_utc": "23:00",
        "quiet_hours_end_utc": "07:00",
    }
    put_res = client.put("/api/v1/notification-preferences/me", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["enabled_channels"] == ["IN_APP"]
    assert updated["min_severity"] == "CRITICAL"
    assert updated["digest_frequency"] == "WEEKLY"
    assert updated["quiet_hours_enabled"] is True


def test_api_principal_authorization_and_role_enforcement(client):
    """Verifies that non-admin/viewer roles are rejected on administrative routes."""
    viewer_headers = {"X-User-Role": "VIEWER", "X-User-Email": "viewer@cloudsage.com"}

    # Viewer attempting to create alert rule should receive 403 Forbidden
    res = client.post(
        "/api/v1/alert-rules",
        json={"name": "Forbidden Rule", "provider": "AWS"},
        headers=viewer_headers,
    )
    assert res.status_code == 403
