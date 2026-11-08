"""
Unit and Integration Tests for Transactional Notification Outbox & Dispatcher.
Tests outbox item lifecycle, attempt recording, latency metrics, exponential backoff,
dead-letter queue (DLQ) threshold, manual retry, and cancellation.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
import uuid
import pytest

from backend.app.core.enums import NotificationChannel, NotificationDeliveryStatus
from backend.app.models.alert import NotificationDeliveryAttempt, NotificationOutbox
from backend.app.alerts.dispatcher import NotificationDispatcherService


def test_outbox_item_initial_state(db_session):
    """Verifies that newly enqueued outbox item has PENDING status and attempts=0."""
    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.IN_APP.value,
        recipient="user-123",
        subject="Cost Spike Notification",
        payload={"alert": "test"},
        status=NotificationDeliveryStatus.PENDING,
        attempts=0,
        max_attempts=5,
    )
    db_session.add(item)
    db_session.commit()

    saved = db_session.query(NotificationOutbox).filter(NotificationOutbox.id == item.id).first()
    assert saved.status == NotificationDeliveryStatus.PENDING
    assert saved.attempts == 0
    assert saved.max_attempts == 5
    assert saved.delivered_at is None


def test_dispatcher_successful_delivery(db_session):
    """Verifies successful delivery transitions item to DELIVERED and records delivery attempt."""
    dispatcher = NotificationDispatcherService()

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.IN_APP.value,
        recipient="finops-lead",
        subject="AWS Anomaly Alert",
        payload={"alert_instance_id": str(uuid.uuid4()), "message": "Test"},
        status=NotificationDeliveryStatus.PENDING,
        attempts=0,
        max_attempts=5,
    )
    db_session.add(item)
    db_session.commit()

    results = dispatcher.process_outbox_batch(db_session, batch_size=10)
    assert len(results) == 1
    delivered = results[0]
    assert delivered.status == NotificationDeliveryStatus.DELIVERED
    assert delivered.delivered_at is not None
    assert delivered.attempts == 1

    # Check attempt audit log
    attempt = (
        db_session.query(NotificationDeliveryAttempt)
        .filter(NotificationDeliveryAttempt.outbox_id == item.id)
        .first()
    )
    assert attempt is not None
    assert attempt.status in ("DELIVERED", "SUCCESS")
    assert attempt.latency_ms is not None
    assert attempt.attempt_number == 1


def test_dispatcher_exponential_backoff_on_failure(db_session):
    """Verifies that a delivery failure triggers exponential backoff and increments attempt counter."""
    dispatcher = NotificationDispatcherService()

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.WEBHOOK.value,
        recipient="https://api.external.com/webhook",
        subject="Webhook Alert",
        payload={"data": "test"},
        status=NotificationDeliveryStatus.PENDING,
        attempts=0,
        max_attempts=5,
    )
    db_session.add(item)
    db_session.commit()

    # Simulate webhook HTTP connection error
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.side_effect = Exception("Simulated connection timeout")
        results = dispatcher.process_outbox_batch(db_session, batch_size=10)

    assert len(results) == 1
    retrying_item = results[0]
    assert retrying_item.status == NotificationDeliveryStatus.RETRYING
    assert retrying_item.attempts == 1
    assert "Simulated connection timeout" in (retrying_item.last_error or "")

    # Next attempt should be scheduled in the future (~2 minutes: 2^1 * 60s)
    now = datetime.now(timezone.utc)
    next_att = retrying_item.next_attempt_at
    if next_att.tzinfo is None:
        next_att = next_att.replace(tzinfo=timezone.utc)
    assert next_att > now


def test_dispatcher_dead_letter_queue_threshold(db_session):
    """Verifies that exceeding max_attempts moves item to DEAD_LETTERED status."""
    dispatcher = NotificationDispatcherService()

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.WEBHOOK.value,
        recipient="https://api.broken.com/webhook",
        subject="Failing Webhook",
        payload={"data": "test"},
        status=NotificationDeliveryStatus.RETRYING,
        attempts=4,  # Next failure will reach 5 (max_attempts)
        max_attempts=5,
        next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(item)
    db_session.commit()

    with patch("urllib.request.urlopen") as mock_open:
        mock_open.side_effect = Exception("Permanent HTTP 500 server error")
        results = dispatcher.process_outbox_batch(db_session, batch_size=10)

    assert len(results) == 1
    dlq_item = results[0]
    assert dlq_item.status == NotificationDeliveryStatus.DEAD_LETTERED
    assert dlq_item.attempts == 5


def test_dispatcher_manual_retry_dead_letter(db_session):
    """Verifies that manual retry re-queues a DEAD_LETTERED item to PENDING."""
    dispatcher = NotificationDispatcherService()

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.WEBHOOK.value,
        recipient="https://api.repaired.com/webhook",
        subject="Dead Lettered Item",
        payload={"data": "test"},
        status=NotificationDeliveryStatus.DEAD_LETTERED,
        attempts=5,
        max_attempts=5,
        last_error="Temporary 503 Service Unavailable",
    )
    db_session.add(item)
    db_session.commit()

    requeued = dispatcher.retry_dead_letter(db_session, item.id)
    assert requeued.status == NotificationDeliveryStatus.PENDING
    assert requeued.attempts == 0
    assert requeued.last_error is None


def test_dispatcher_cancel_notification(db_session):
    """Verifies cancelling a pending or retrying outbox notification."""
    dispatcher = NotificationDispatcherService()

    item = NotificationOutbox(
        id=uuid.uuid4(),
        channel=NotificationChannel.EMAIL.value,
        recipient="devnull@example.com",
        subject="Cancel Me",
        payload={"data": "test"},
        status=NotificationDeliveryStatus.RETRYING,
        attempts=2,
        max_attempts=5,
    )
    db_session.add(item)
    db_session.commit()

    cancelled = dispatcher.cancel_notification(db_session, item.id)
    assert cancelled.status == NotificationDeliveryStatus.CANCELLED
