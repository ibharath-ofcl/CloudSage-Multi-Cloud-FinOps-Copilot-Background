"""
CloudSage Notification Dispatcher & Outbox Processor.
Processes the transactional notification outbox, handles exponential backoff retries,
logs delivery attempt diagnostics, and manages dead-letter queue escalation.
"""

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from backend.app.core.enums import NotificationChannel, NotificationDeliveryStatus
from backend.app.models.alert import (
    NotificationDeliveryAttempt,
    NotificationLog,
    NotificationOutbox,
)
from backend.app.alerts.providers import (
    EmailNotificationProvider,
    InAppNotificationProvider,
    SlackNotificationProvider,
    TeamsNotificationProvider,
    WebhookNotificationProvider,
)

logger = logging.getLogger(__name__)


class NotificationDispatcherService:
    """
    Transactional outbox processor and delivery dispatcher.
    Provides at-least-once delivery, bounded retries, and error isolation.
    """

    @classmethod
    def get_provider(cls, channel: str):
        """Resolves notification provider for given channel."""
        ch = channel.upper().strip()
        if ch == NotificationChannel.IN_APP.value:
            return InAppNotificationProvider()
        elif ch == NotificationChannel.EMAIL.value:
            return EmailNotificationProvider()
        elif ch == NotificationChannel.WEBHOOK.value:
            return WebhookNotificationProvider(allow_test_destinations=False)
        elif ch == NotificationChannel.SLACK.value:
            return SlackNotificationProvider(allow_test_destinations=True)
        elif ch == NotificationChannel.TEAMS.value:
            return TeamsNotificationProvider(allow_test_destinations=True)
        else:
            return WebhookNotificationProvider(allow_test_destinations=True)

    @classmethod
    def dispatch_outbox_item(cls, db: Session, outbox_id: uuid.UUID) -> bool:
        """
        Dispatches a single outbox record with latency measurement and attempt logging.
        """
        outbox: Optional[NotificationOutbox] = (
            db.query(NotificationOutbox).filter(NotificationOutbox.id == outbox_id).first()
        )
        if not outbox:
            logger.warning(f"NotificationOutbox item '{outbox_id}' not found.")
            return False

        if outbox.status in (NotificationDeliveryStatus.DELIVERED.value, NotificationDeliveryStatus.CANCELLED.value):
            return True

        now = datetime.now(timezone.utc)
        outbox.status = NotificationDeliveryStatus.PROCESSING.value
        outbox.attempts += 1
        outbox.last_attempt_at = now
        db.flush()

        provider = cls.get_provider(outbox.channel)
        start_time = time.perf_counter()

        try:
            success, code, body, err = provider.dispatch(
                recipient=outbox.recipient,
                subject=outbox.subject,
                payload=outbox.payload,
            )
        except Exception as exc:
            success, code, body, err = False, 500, "", str(exc)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Log delivery attempt audit record
        attempt = NotificationDeliveryAttempt(
            id=uuid.uuid4(),
            outbox_id=outbox.id,
            attempt_number=outbox.attempts,
            channel=outbox.channel,
            recipient=outbox.recipient,
            status="SUCCESS" if success else "FAILED",
            response_code=code,
            response_body=body[:500] if body else None,
            latency_ms=elapsed_ms,
            error_message=err if err else None,
            attempted_at=now,
        )
        db.add(attempt)

        if success:
            outbox.status = NotificationDeliveryStatus.DELIVERED.value
            outbox.delivered_at = now
            outbox.last_error = None

            # Legacy NotificationLog write for backward compatibility
            try:
                legacy_log = NotificationLog(
                    id=uuid.uuid4(),
                    alert_rule_id=uuid.UUID(outbox.payload.get("alert_rule_id")) if outbox.payload.get("alert_rule_id") else None,
                    channel=outbox.channel,
                    recipient=outbox.recipient,
                    payload=outbox.payload,
                    status="DELIVERED",
                    dispatched_at=now,
                )
                db.add(legacy_log)
            except Exception:
                pass

        else:
            outbox.last_error = err
            if outbox.attempts < outbox.max_attempts:
                # Exponential backoff: 2^attempts * 60 seconds
                backoff_seconds = (2 ** outbox.attempts) * 60
                outbox.status = NotificationDeliveryStatus.RETRYING.value
                outbox.next_attempt_at = now + timedelta(seconds=backoff_seconds)
            else:
                outbox.status = NotificationDeliveryStatus.DEAD_LETTERED.value

        db.commit()
        db.refresh(outbox)
        return success

    @classmethod
    def process_pending_outbox(cls, db: Session, limit: int = 50) -> Dict[str, int]:
        """
        Pulls pending or retryable outbox items whose next_attempt_at has arrived.
        """
        now = datetime.now(timezone.utc)
        items = (
            db.query(NotificationOutbox)
            .filter(
                NotificationOutbox.status.in_([
                    NotificationDeliveryStatus.PENDING.value,
                    NotificationDeliveryStatus.RETRYING.value,
                ]),
                NotificationOutbox.next_attempt_at <= now,
            )
            .order_by(NotificationOutbox.created_at.asc())
            .limit(limit)
            .all()
        )

        counts = {"total": len(items), "delivered": 0, "retrying": 0, "dead_lettered": 0}

        for item in items:
            try:
                ok = cls.dispatch_outbox_item(db, item.id)
                if ok:
                    counts["delivered"] += 1
                elif item.status == NotificationDeliveryStatus.DEAD_LETTERED.value:
                    counts["dead_lettered"] += 1
                else:
                    counts["retrying"] += 1
            except Exception as e:
                logger.error(f"Error processing outbox {item.id}: {e}", exc_info=True)

        return counts

    @classmethod
    def process_outbox_batch(cls, db: Session, batch_size: int = 50) -> List[NotificationOutbox]:
        """Pulls and processes pending outbox items, returning list of processed records."""
        now = datetime.now(timezone.utc)
        items = (
            db.query(NotificationOutbox)
            .filter(
                NotificationOutbox.status.in_([
                    NotificationDeliveryStatus.PENDING.value,
                    NotificationDeliveryStatus.RETRYING.value,
                ]),
                NotificationOutbox.next_attempt_at <= now,
            )
            .order_by(NotificationOutbox.created_at.asc())
            .limit(batch_size)
            .all()
        )
        processed = []
        for item in items:
            try:
                cls.dispatch_outbox_item(db, item.id)
                db.refresh(item)
                processed.append(item)
            except Exception as e:
                logger.error(f"Error processing outbox {item.id}: {e}", exc_info=True)
                processed.append(item)
        return processed

    @classmethod
    def retry_outbox_item(cls, db: Session, outbox_id: uuid.UUID) -> NotificationOutbox:
        """
        Allows an authorized operator to manually re-queue a failed or dead-lettered notification.
        """
        outbox: Optional[NotificationOutbox] = (
            db.query(NotificationOutbox).filter(NotificationOutbox.id == outbox_id).first()
        )
        if not outbox:
            raise ValueError(f"NotificationOutbox item '{outbox_id}' not found.")

        now = datetime.now(timezone.utc)
        outbox.status = NotificationDeliveryStatus.PENDING.value
        outbox.next_attempt_at = now
        outbox.attempts = 0
        outbox.last_error = None
        db.commit()
        db.refresh(outbox)
        return outbox

    @classmethod
    def retry_dead_letter(cls, db: Session, outbox_id: uuid.UUID) -> NotificationOutbox:
        """Alias for retry_outbox_item."""
        return cls.retry_outbox_item(db, outbox_id)

    @classmethod
    def cancel_outbox_item(cls, db: Session, outbox_id: uuid.UUID) -> NotificationOutbox:
        """Cancels a pending or retrying outbox notification."""
        outbox: Optional[NotificationOutbox] = (
            db.query(NotificationOutbox).filter(NotificationOutbox.id == outbox_id).first()
        )
        if not outbox:
            raise ValueError(f"NotificationOutbox item '{outbox_id}' not found.")

        if outbox.status in (NotificationDeliveryStatus.DELIVERED.value, NotificationDeliveryStatus.CANCELLED.value):
            return outbox

        outbox.status = NotificationDeliveryStatus.CANCELLED.value
        db.commit()
        db.refresh(outbox)
        return outbox

    @classmethod
    def cancel_notification(cls, db: Session, outbox_id: uuid.UUID) -> NotificationOutbox:
        """Alias for cancel_outbox_item."""
        return cls.cancel_outbox_item(db, outbox_id)
