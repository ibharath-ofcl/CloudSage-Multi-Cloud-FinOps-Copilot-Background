"""
CloudSage Alerting & Notification Hub Celery Tasks.
Provides background execution for:
1. Transactional outbox dispatching (exponential backoff & DLQ).
2. Cost anomaly alert evaluation against active rules.
3. Daily notification digest compilation and dispatch.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from decimal import Decimal

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.alerts.dispatcher import NotificationDispatcherService
from backend.app.alerts.evaluation import AlertRuleEvaluationService
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.alert import NotificationPreference, AlertInstance, NotificationOutbox
from backend.app.core.enums import NotificationChannel

try:
    from celery import Celery
    celery_app = Celery(
        "cloudsage_tasks",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
    )
    HAS_CELERY = True
except Exception:
    celery_app = None
    HAS_CELERY = False


def execute_outbox_dispatch_job(batch_size: int = 50) -> Dict[str, Any]:
    """
    Process pending and retry-ready items in the notification outbox.
    Returns summary statistics.
    """
    session = SyncSessionLocal()
    dispatcher = NotificationDispatcherService()
    try:
        results = dispatcher.process_outbox_batch(session, batch_size=batch_size)
        return {
            "processed_count": len(results),
            "delivered": sum(1 for r in results if r.status.value == "DELIVERED"),
            "retrying": sum(1 for r in results if r.status.value == "RETRYING"),
            "dead_lettered": sum(1 for r in results if r.status.value == "DEAD_LETTERED"),
            "failed": sum(1 for r in results if r.status.value == "FAILED"),
        }
    finally:
        session.close()


def execute_anomaly_alert_evaluation_job(
    anomaly_ids: Optional[List[str]] = None,
    lookback_hours: int = 24,
) -> Dict[str, Any]:
    """
    Evaluate active alert rules against cost anomalies.
    If anomaly_ids is not provided, evaluates against anomalies detected in the last lookback_hours.
    """
    session = SyncSessionLocal()
    evaluator = AlertRuleEvaluationService()
    try:
        query = session.query(CostAnomaly)
        if anomaly_ids:
            query = query.filter(CostAnomaly.anomaly_id.in_(anomaly_ids))
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            query = query.filter(CostAnomaly.detected_at >= cutoff)

        anomalies = query.all()
        created_alerts_count = 0
        suppressed_count = 0
        escalated_count = 0
        outbox_enqueued_count = 0

        for anomaly in anomalies:
            instances = evaluator.evaluate_anomaly(session, anomaly)
            for inst in instances:
                created_alerts_count += 1
                if inst.is_suppressed:
                    suppressed_count += 1
                if inst.severity_escalated:
                    escalated_count += 1
                # Check associated outbox count
                outbox_items = (
                    session.query(NotificationOutbox)
                    .filter(NotificationOutbox.alert_instance_id == inst.alert_instance_id)
                    .all()
                )
                outbox_enqueued_count += len(outbox_items)

        session.commit()
        return {
            "anomalies_evaluated": len(anomalies),
            "alert_instances_created": created_alerts_count,
            "suppressed_alerts": suppressed_count,
            "escalated_alerts": escalated_count,
            "outbox_enqueued": outbox_enqueued_count,
        }
    finally:
        session.close()


def execute_daily_digest_job() -> Dict[str, Any]:
    """
    Compile and dispatch daily digests for users subscribed to DAILY digest.
    """
    session = SyncSessionLocal()
    try:
        prefs = (
            session.query(NotificationPreference)
            .filter(
                NotificationPreference.digest_frequency == "DAILY",
                NotificationPreference.email_enabled == True,
            )
            .all()
        )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_alerts = (
            session.query(AlertInstance)
            .filter(AlertInstance.triggered_at >= cutoff)
            .all()
        )

        digests_created = 0
        if recent_alerts:
            total_impact = sum(
                (a.total_cost_impact for a in recent_alerts if a.total_cost_impact),
                Decimal("0.0000"),
            )
            for pref in prefs:
                if not pref.user_id:
                    continue
                # Enqueue daily digest into outbox
                outbox_item = NotificationOutbox(
                    channel=NotificationChannel.EMAIL,
                    recipient=pref.user_id,  # Or user email if resolved
                    subject=f"[CloudSage] Daily FinOps Cost Anomaly Digest - {len(recent_alerts)} Alerts",
                    body_text=(
                        f"Daily FinOps Digest:\n"
                        f"Total alerts in last 24h: {len(recent_alerts)}\n"
                        f"Total financial impact: ${total_impact:,.2f}\n"
                        f"Review your alerts at: /alerts\n"
                    ),
                    body_html=(
                        f"<h2>CloudSage Daily Cost Anomaly Digest</h2>"
                        f"<p>In the last 24 hours, <strong>{len(recent_alerts)}</strong> cost anomalies triggered alert rules.</p>"
                        f"<p>Total Financial Impact: <strong>${total_impact:,.2f}</strong></p>"
                        f"<p><em>Advisory Notice: CloudSage is strictly advisory. No cloud infrastructure has been modified.</em></p>"
                    ),
                    metadata_json={
                        "type": "DAILY_DIGEST",
                        "alert_count": len(recent_alerts),
                        "total_impact": str(total_impact),
                    },
                )
                session.add(outbox_item)
                digests_created += 1

            session.commit()

        return {
            "preferences_checked": len(prefs),
            "alerts_in_window": len(recent_alerts),
            "digests_enqueued": digests_created,
        }
    finally:
        session.close()


if HAS_CELERY and celery_app:
    @celery_app.task(name="cloudsage.alerts.dispatch_outbox")
    def dispatch_outbox_task(batch_size: int = 50) -> Dict[str, Any]:
        """Background worker task for outbox delivery."""
        return execute_outbox_dispatch_job(batch_size=batch_size)

    @celery_app.task(name="cloudsage.alerts.evaluate_anomalies")
    def evaluate_anomalies_task(
        anomaly_ids: Optional[List[str]] = None,
        lookback_hours: int = 24,
    ) -> Dict[str, Any]:
        """Background worker task for evaluating anomalies."""
        return execute_anomaly_alert_evaluation_job(
            anomaly_ids=anomaly_ids,
            lookback_hours=lookback_hours,
        )

    @celery_app.task(name="cloudsage.alerts.send_daily_digest")
    def send_daily_digest_task() -> Dict[str, Any]:
        """Background worker task for sending daily digests."""
        return execute_daily_digest_job()
