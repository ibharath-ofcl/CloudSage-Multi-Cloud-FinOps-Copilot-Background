"""
Unit and Integration Tests for In-App Notification Center.
Tests in-app notification creation, user/role scoping, unread counter badge,
mark read, mark unread, and mark-all-read bulk operations.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import Severity
from backend.app.models.alert import InAppNotification


def create_in_app_notification(
    db_session,
    recipient: str = "finops-lead",
    is_read: bool = False,
    severity: str = "HIGH",
    title: str = "GCP Anomaly Alert",
) -> InAppNotification:
    notif = InAppNotification(
        id=uuid.uuid4(),
        recipient_user_id=recipient,
        title=title,
        message="Unexpected surge in Google Kubernetes Engine cluster spend.",
        severity=severity,
        provider="GCP",
        account_id="gcp-prod-infra",
        service_name="Kubernetes Engine",
        excess_cost=Decimal("250.0000"),
        is_read=is_read,
        read_at=datetime.now(timezone.utc) if is_read else None,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)
    return notif


def test_in_app_notification_creation_and_attributes(db_session):
    """Verifies creation and field values of an in-app notification."""
    notif = create_in_app_notification(db_session, recipient="alice@company.com", is_read=False)

    assert notif.id is not None
    assert notif.recipient_user_id == "alice@company.com"
    assert notif.title == "GCP Anomaly Alert"
    assert notif.is_read is False
    assert notif.read_at is None
    assert notif.excess_cost == Decimal("250.0000")


def test_unread_count_calculation(db_session):
    """Verifies unread counter matches total unread items for a specific recipient."""
    recipient = "bob@company.com"

    # Create 3 unread, 2 read
    for i in range(3):
        create_in_app_notification(db_session, recipient=recipient, is_read=False, title=f"Unread {i}")
    for i in range(2):
        create_in_app_notification(db_session, recipient=recipient, is_read=True, title=f"Read {i}")

    # Another user's unread
    create_in_app_notification(db_session, recipient="charlie@company.com", is_read=False)

    unread_bob = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.recipient_user_id == recipient, InAppNotification.is_read == False)
        .count()
    )
    assert unread_bob == 3


def test_mark_single_notification_read_and_unread(db_session):
    """Verifies marking notification read sets timestamp, and unread resets it."""
    notif = create_in_app_notification(db_session, is_read=False)
    assert notif.is_read is False
    assert notif.read_at is None

    # Mark Read
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db_session.commit()

    refreshed = db_session.query(InAppNotification).filter(InAppNotification.id == notif.id).first()
    assert refreshed.is_read is True
    assert refreshed.read_at is not None

    # Mark Unread
    refreshed.is_read = False
    refreshed.read_at = None
    db_session.commit()

    re_refreshed = db_session.query(InAppNotification).filter(InAppNotification.id == notif.id).first()
    assert re_refreshed.is_read is False
    assert re_refreshed.read_at is None


def test_mark_all_as_read_bulk(db_session):
    """Verifies marking all notifications as read updates all pending notifications for user."""
    recipient = "team-finops"
    for i in range(4):
        create_in_app_notification(db_session, recipient=recipient, is_read=False)

    now = datetime.now(timezone.utc)
    updated_count = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.recipient_user_id == recipient, InAppNotification.is_read == False)
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db_session.commit()

    assert updated_count == 4

    remaining_unread = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.recipient_user_id == recipient, InAppNotification.is_read == False)
        .count()
    )
    assert remaining_unread == 0


def test_filter_unread_only(db_session):
    """Verifies unread filtering excludes read notifications."""
    recipient = "engineer-1"
    n1 = create_in_app_notification(db_session, recipient=recipient, is_read=False, title="New Alert")
    n2 = create_in_app_notification(db_session, recipient=recipient, is_read=True, title="Old Alert")

    query = db_session.query(InAppNotification).filter(
        InAppNotification.recipient_user_id == recipient,
        InAppNotification.is_read == False,
    )
    results = query.all()
    assert len(results) == 1
    assert results[0].id == n1.id
