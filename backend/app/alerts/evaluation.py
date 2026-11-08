"""
CloudSage Alert Rule Evaluation Service.
Evaluates cost anomalies against configured alert rules, applies multi-dimensional scoping,
enforces deduplication, cooldown windows, severity escalation, and creates transactional outbox entries.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.core.enums import (
    AlertStatus,
    NotificationChannel,
    NotificationDeliveryStatus,
    Severity,
)
from backend.app.models.alert import (
    AlertHistory,
    AlertInstance,
    AlertRule,
    InAppNotification,
    NotificationOutbox,
)
from backend.app.models.anomaly import CostAnomaly

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    Severity.LOW.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.HIGH.value: 3,
    Severity.CRITICAL.value: 4,
}


class AlertRuleEvaluationService:
    """
    Evaluates newly identified or updated cost anomalies against active alert rules.
    Decoupled from detection so alert failures never impede statistical baselining.
    """

    @classmethod
    def evaluate_anomaly(
        cls,
        db: Session,
        anomaly: CostAnomaly,
        auto_commit: bool = True,
    ) -> List[AlertInstance]:
        """
        Evaluates a single CostAnomaly against all enabled alert rules.
        Returns the list of generated or updated AlertInstance records.
        """
        now = datetime.now(timezone.utc)
        created_or_updated_alerts: List[AlertInstance] = []

        # 1. Fetch enabled and non-archived rules
        rules: List[AlertRule] = (
            db.query(AlertRule)
            .filter(AlertRule.is_enabled == True, AlertRule.is_archived == False)
            .all()
        )

        for rule in rules:
            try:
                # Use a nested transaction savepoint for rule evaluation safety
                with db.begin_nested():
                    if not cls._matches_rule(rule, anomaly):
                        continue

                    # 2. Compute deterministic deduplication key
                    dedup_key = cls._compute_dedup_key(rule, anomaly)

                    # 3. Check for existing alert instance
                    existing: Optional[AlertInstance] = (
                        db.query(AlertInstance)
                        .filter(AlertInstance.dedup_key == dedup_key)
                        .first()
                    )

                    if existing:
                        # Case A: Active Suppression
                        suppress_until = existing.suppress_until
                        if suppress_until and suppress_until.tzinfo is None:
                            suppress_until = suppress_until.replace(tzinfo=timezone.utc)
                        if suppress_until and suppress_until > now:
                            logger.info(f"Alert {existing.id} suppressed until {suppress_until}.")
                            created_or_updated_alerts.append(existing)
                            continue

                        # Case B: Cooldown & Escalation Evaluation
                        last_triggered = existing.last_triggered_at
                        if last_triggered and last_triggered.tzinfo is None:
                            last_triggered = last_triggered.replace(tzinfo=timezone.utc)

                        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
                        within_cooldown = (now - last_triggered) < cooldown_delta

                        old_level = SEVERITY_ORDER.get(existing.severity, 1)
                        new_level = SEVERITY_ORDER.get(anomaly.severity, 1)

                        if within_cooldown:
                            if new_level > old_level:
                                # Material Severity Escalation!
                                prev_sev = existing.severity
                                existing.severity = anomaly.severity
                                existing.current_cost = anomaly.actual_cost
                                existing.excess_cost = anomaly.estimated_excess_cost
                                existing.percentage_deviation = anomaly.spike_percentage
                                existing.escalation_level += 1
                                existing.last_escalated_at = now
                                existing.last_triggered_at = now
                                existing.trigger_count += 1

                                hist = AlertHistory(
                                    id=uuid.uuid4(),
                                    alert_instance_id=existing.id,
                                    from_status=existing.status,
                                    to_status=existing.status,
                                    actor="evaluation_engine",
                                    action="ESCALATE",
                                    notes=f"Severity escalated from {prev_sev} to {anomaly.severity}. Excess cost: ${anomaly.estimated_excess_cost} USD.",
                                    details={
                                        "previous_severity": prev_sev,
                                        "new_severity": anomaly.severity,
                                        "excess_cost": str(anomaly.estimated_excess_cost),
                                    },
                                    created_at=now,
                                )
                                db.add(hist)
                                cls._enqueue_notifications(db, existing, rule, is_escalation=True)
                                created_or_updated_alerts.append(existing)
                            else:
                                # Cooldown active, no escalation: increment count, do not re-alert!
                                existing.trigger_count += 1
                                existing.last_triggered_at = now
                                db.flush()
                                created_or_updated_alerts.append(existing)
                        else:
                            # Cooldown has elapsed: update trigger and reopen if previously resolved
                            existing.trigger_count += 1
                            existing.last_triggered_at = now
                            if existing.status in (AlertStatus.RESOLVED.value, AlertStatus.CLOSED.value):
                                prev_st = existing.status
                                existing.status = AlertStatus.OPEN.value
                                hist = AlertHistory(
                                    id=uuid.uuid4(),
                                    alert_instance_id=existing.id,
                                    from_status=prev_st,
                                    to_status=AlertStatus.OPEN.value,
                                    actor="evaluation_engine",
                                    action="REOPEN",
                                    notes=f"Anomaly recurring after cooldown period expired: {anomaly.title}",
                                    details={"recurrence": True},
                                    created_at=now,
                                )
                                db.add(hist)
                                cls._enqueue_notifications(db, existing, rule, is_escalation=False)
                            created_or_updated_alerts.append(existing)

                    else:
                        # Case C: Newly Triggered Alert Instance
                        title = f"Cost Alert: {anomaly.title or anomaly.service_name}"
                        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
                        alert = AlertInstance(
                            id=uuid.uuid4(),
                            alert_rule_id=rule.id,
                            anomaly_id=anomaly.id,
                            dedup_key=dedup_key,
                            title=title,
                            severity=anomaly.severity,
                            current_cost=anomaly.actual_cost,
                            expected_cost=anomaly.expected_cost,
                            excess_cost=anomaly.estimated_excess_cost,
                            percentage_deviation=anomaly.spike_percentage,
                            status=AlertStatus.OPEN.value,
                            provider=anomaly.provider,
                            account_id=anomaly.account_id,
                            service_name=anomaly.service_name,
                            region=anomaly.region,
                            resource_id=anomaly.resource_id,
                            trigger_count=1,
                            first_triggered_at=now,
                            last_triggered_at=now,
                            escalation_level=0,
                            created_at=now,
                            updated_at=now,
                        )
                        db.add(alert)
                        db.flush()

                        # Audit Log Entry
                        hist = AlertHistory(
                            id=uuid.uuid4(),
                            alert_instance_id=alert.id,
                            from_status=None,
                            to_status=AlertStatus.OPEN.value,
                            actor="evaluation_engine",
                            action="CREATE",
                            notes=f"Alert generated by rule '{rule.name}' for excess spend of ${anomaly.estimated_excess_cost} USD.",
                            details={
                                "rule_id": str(rule.id),
                                "rule_name": rule.name,
                                "excess_cost": str(anomaly.estimated_excess_cost),
                                "z_score": str(anomaly.z_score),
                            },
                            created_at=now,
                        )
                        db.add(hist)

                        # Enqueue Multi-Channel Notifications into Transactional Outbox
                        cls._enqueue_notifications(db, alert, rule, is_escalation=False)
                        created_or_updated_alerts.append(alert)

            except Exception as rule_err:
                logger.error(f"Error evaluating rule {rule.id} against anomaly {anomaly.id}: {rule_err}", exc_info=True)

        if auto_commit:
            db.commit()

        return created_or_updated_alerts

    @classmethod
    def _matches_rule(cls, rule: AlertRule, anomaly: CostAnomaly) -> bool:
        """Evaluates whether an anomaly meets all dimensional and financial criteria of a rule."""
        # 1. Provider Scope
        if rule.provider != "ALL" and rule.provider.upper() != anomaly.provider.upper():
            return False

        # 2. Account Scope
        if rule.account_id and rule.account_id.strip() != anomaly.account_id.strip():
            return False

        # 3. Region Scope
        if rule.region and rule.region.strip().lower() != anomaly.region.strip().lower():
            return False

        # 4. Service Scope
        if rule.service_name and rule.service_name.strip().lower() not in anomaly.service_name.strip().lower():
            return False

        # 5. Anomaly Category Scope
        if rule.anomaly_category and rule.anomaly_category.strip().upper() != anomaly.anomaly_category.strip().upper():
            return False

        # 6. Severity Threshold (Hierarchical)
        rule_sev_level = SEVERITY_ORDER.get(rule.min_severity.upper(), 1)
        anomaly_sev_level = SEVERITY_ORDER.get(anomaly.severity.upper(), 1)
        if anomaly_sev_level < rule_sev_level:
            return False

        # 7. Financial & Deviation Thresholds (Strict Decimal comparison!)
        if anomaly.estimated_excess_cost < rule.min_excess_cost:
            return False

        if anomaly.spike_percentage < rule.percentage_deviation_threshold:
            return False

        if anomaly.absolute_deviation < rule.absolute_deviation_threshold:
            return False

        return True

    @classmethod
    def generate_dedup_key(
        cls,
        provider: str,
        account_id: str,
        service_name: str,
        region: str,
        resource_id: Optional[str],
        rule_id: Any,
    ) -> str:
        """Constructs a deterministic composite deduplication fingerprint."""
        if resource_id:
            return f"res:{provider}:{resource_id}:{rule_id}"
        return f"acct:{provider}:{account_id}:{service_name}:{region}:{rule_id}"

    @classmethod
    def _compute_dedup_key(cls, rule: AlertRule, anomaly: CostAnomaly) -> str:
        """Constructs a deterministic composite deduplication fingerprint."""
        return cls.generate_dedup_key(
            provider=anomaly.provider,
            account_id=anomaly.account_id,
            service_name=anomaly.service_name,
            region=anomaly.region,
            resource_id=anomaly.resource_id,
            rule_id=rule.id,
        )

    @classmethod
    def compute_deduplication_key(cls, rule: AlertRule, anomaly: CostAnomaly) -> str:
        """Public alias for computing deduplication fingerprint."""
        return cls._compute_dedup_key(rule, anomaly)

    @classmethod
    def _enqueue_notifications(
        cls,
        db: Session,
        alert: AlertInstance,
        rule: AlertRule,
        is_escalation: bool = False,
    ) -> None:
        """
        Creates In-App and external outbox entries in a transactional manner.
        """
        now = datetime.now(timezone.utc)
        channels = [ch.upper() for ch in (rule.channels or ["IN_APP"])]
        subject = f"{'[ESCALATED] ' if is_escalation else ''}{alert.severity} Alert: {alert.title}"

        payload = {
            "alert_instance_id": str(alert.id),
            "alert_rule_id": str(rule.id),
            "rule_name": rule.name,
            "anomaly_id": str(alert.anomaly_id),
            "title": alert.title,
            "severity": alert.severity,
            "provider": alert.provider,
            "account_id": alert.account_id,
            "service_name": alert.service_name,
            "region": alert.region,
            "resource_id": alert.resource_id,
            "current_cost": str(alert.current_cost),
            "expected_cost": str(alert.expected_cost),
            "excess_cost": str(alert.excess_cost),
            "percentage_deviation": str(alert.percentage_deviation),
            "is_escalation": is_escalation,
            "explanation": f"Cost surge of +${alert.excess_cost} USD (+{alert.percentage_deviation}%) detected on {alert.service_name}.",
        }

        # 1. In-App Notification Center
        if "IN_APP" in channels:
            in_app = InAppNotification(
                id=uuid.uuid4(),
                alert_instance_id=alert.id,
                recipient_user_id="ALL",
                title=subject,
                message=payload["explanation"],
                severity=alert.severity,
                provider=alert.provider,
                account_id=alert.account_id,
                service_name=alert.service_name,
                excess_cost=alert.excess_cost,
                is_read=False,
                action_url=f"/alerts/{alert.id}",
                created_at=now,
            )
            db.add(in_app)

            outbox_inapp = NotificationOutbox(
                id=uuid.uuid4(),
                alert_instance_id=alert.id,
                channel=NotificationChannel.IN_APP.value,
                recipient="in_app_center",
                subject=subject,
                payload=payload,
                status=NotificationDeliveryStatus.DELIVERED.value,
                attempts=1,
                max_attempts=1,
                next_attempt_at=now,
                delivered_at=now,
                created_at=now,
            )
            db.add(outbox_inapp)

        # 2. External Outbox Destinations (Email, Webhook, Slack, Teams)
        recipients = rule.recipients or []
        for ch in channels:
            if ch == "IN_APP":
                continue

            target_recipients = [r for r in recipients if cls._matches_channel_recipient(ch, r)]
            # If no channel-specific recipients, use all recipients for that channel
            if not target_recipients and recipients:
                target_recipients = recipients

            # Default fallback recipient if none configured
            if not target_recipients:
                target_recipients = ["finops-alerts@company.internal"]

            for rec in target_recipients:
                outbox_entry = NotificationOutbox(
                    id=uuid.uuid4(),
                    alert_instance_id=alert.id,
                    channel=ch,
                    recipient=rec,
                    subject=subject,
                    payload=payload,
                    status=NotificationDeliveryStatus.PENDING.value,
                    attempts=0,
                    max_attempts=5,
                    next_attempt_at=now,
                    created_at=now,
                )
                db.add(outbox_entry)

    @staticmethod
    def _matches_channel_recipient(channel: str, recipient: str) -> bool:
        """Determines whether a recipient string matches the channel format."""
        if channel == "EMAIL":
            return "@" in recipient and not recipient.startswith("http")
        if channel in ("WEBHOOK", "SLACK", "TEAMS"):
            return recipient.startswith("http://") or recipient.startswith("https://")
        return True

    @classmethod
    def preview_rule(
        cls,
        db: Session,
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        min_severity: str = "MEDIUM",
        min_excess_cost: Decimal = Decimal("0.0000"),
        percentage_deviation_threshold: Decimal = Decimal("0.00"),
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Evaluates rule criteria against historical cost anomalies in dry-run mode without mutating state.
        """
        query = db.query(CostAnomaly).order_by(desc(CostAnomaly.detected_at)).limit(limit)
        anomalies = query.all()

        severity_order = {
            Severity.LOW.value: 1,
            Severity.MEDIUM.value: 2,
            Severity.HIGH.value: 3,
            Severity.CRITICAL.value: 4,
        }
        min_sev_rank = severity_order.get(min_severity.upper(), 2)

        matches: List[Dict[str, Any]] = []
        for a in anomalies:
            if provider and provider.upper() != "ALL":
                if a.provider.upper() != provider.upper():
                    continue
            if account_id and a.account_id != account_id:
                continue

            sev_rank = severity_order.get(a.severity.value if hasattr(a.severity, "value") else str(a.severity).upper(), 1)
            if sev_rank < min_sev_rank:
                continue

            excess = Decimal(str(a.estimated_excess_cost or "0.0000"))
            if excess < min_excess_cost:
                continue

            pct = Decimal(str(a.spike_percentage or "0.00"))
            if pct < percentage_deviation_threshold:
                continue

            matches.append({
                "anomaly_id": str(a.id),
                "provider": a.provider.value if hasattr(a.provider, "value") else str(a.provider),
                "account_id": a.account_id,
                "service_name": a.service_name,
                "region": a.region,
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "actual_cost": str(a.actual_cost),
                "expected_cost": str(a.expected_cost),
                "estimated_excess_cost": str(a.estimated_excess_cost),
                "spike_percentage": str(a.spike_percentage),
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            })

        return {
            "matched_count": len(matches),
            "sample_matches": matches[:10],
            "estimated_alert_frequency_30d": len(matches),
        }
