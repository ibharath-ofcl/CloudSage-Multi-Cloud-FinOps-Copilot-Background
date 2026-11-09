"""
CloudSage Security Monitoring & Threat Detection Service.
Detects:
- Repeated authentication failures & brute-force attacks
- Account lockouts
- Cross-tenant probing & IDOR attempts
- Privilege escalation attempts
- Suspicious bulk data exports
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.enums import SecurityEventSeverity, SecurityEventType
from backend.app.models.security import SecurityEvent
from backend.app.models.user import User


class ThreatDetectionService:
    """Detects, logs, and mitigates security threats and abnormal access patterns."""

    @classmethod
    def record_event(
        cls,
        db: Session,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        user_email: Optional[str] = None,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        source_ip: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityEvent:
        """Records an auditable security threat or authentication event."""
        now = datetime.now(timezone.utc)
        event = SecurityEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            event_type=event_type.value if hasattr(event_type, "value") else str(event_type),
            severity=severity.value if hasattr(severity, "value") else str(severity),
            source_ip=source_ip,
            endpoint=endpoint,
            details=details or {},
            timestamp=now,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def handle_failed_login(
        cls,
        db: Session,
        email: str,
        source_ip: Optional[str] = None,
        endpoint: Optional[str] = "/api/v1/auth/login",
    ) -> None:
        """Increments failed login counter, detects brute force, and applies temporary lockout."""
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        now = datetime.now(timezone.utc)

        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            attempts = user.failed_login_attempts
            max_attempts = settings.LOGIN_MAX_FAILED_ATTEMPTS

            if attempts >= max_attempts:
                lockout_duration = settings.LOGIN_LOCKOUT_MINUTES
                user.is_locked = True
                user.locked_until = now + timedelta(minutes=lockout_duration)

                cls.record_event(
                    db=db,
                    event_type=SecurityEventType.ACCOUNT_LOCKED,
                    severity=SecurityEventSeverity.CRITICAL,
                    user_email=user.email,
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    source_ip=source_ip,
                    endpoint=endpoint,
                    details={
                        "failed_attempts": attempts,
                        "lockout_minutes": lockout_duration,
                        "locked_until": user.locked_until.isoformat(),
                    },
                )
            else:
                cls.record_event(
                    db=db,
                    event_type=SecurityEventType.LOGIN_FAILURE,
                    severity=SecurityEventSeverity.MEDIUM if attempts < 3 else SecurityEventSeverity.HIGH,
                    user_email=user.email,
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    source_ip=source_ip,
                    endpoint=endpoint,
                    details={"failed_attempts": attempts, "threshold": max_attempts},
                )
            db.commit()
        else:
            # User not found; still record failed attempt against email to detect enumeration
            cls.record_event(
                db=db,
                event_type=SecurityEventType.LOGIN_FAILURE,
                severity=SecurityEventSeverity.LOW,
                user_email=email,
                source_ip=source_ip,
                endpoint=endpoint,
                details={"reason": "User does not exist"},
            )

    @classmethod
    def handle_successful_login(
        cls,
        db: Session,
        user: User,
        source_ip: Optional[str] = None,
        endpoint: Optional[str] = "/api/v1/auth/login",
    ) -> None:
        """Resets failed attempt counters and records successful authentication."""
        now = datetime.now(timezone.utc)
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.last_login_at = now
        db.commit()

        cls.record_event(
            db=db,
            event_type=SecurityEventType.LOGIN_SUCCESS,
            severity=SecurityEventSeverity.INFORMATIONAL,
            user_email=user.email,
            user_id=user.id,
            tenant_id=user.tenant_id,
            source_ip=source_ip,
            endpoint=endpoint,
            details={"role": user.role},
        )

    @classmethod
    def get_security_stats(
        cls,
        db: Session,
        tenant_id: Optional[UUID] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Calculates security telemetry and threat indicators."""
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        query = db.query(SecurityEvent).filter(SecurityEvent.timestamp >= since)
        if tenant_id:
            query = query.filter(SecurityEvent.tenant_id == tenant_id)

        all_events = query.all()
        total_events = len(all_events)
        critical_events = sum(1 for e in all_events if e.severity == SecurityEventSeverity.CRITICAL.value)
        high_events = sum(1 for e in all_events if e.severity == SecurityEventSeverity.HIGH.value)
        failed_logins = sum(1 for e in all_events if e.event_type == SecurityEventType.LOGIN_FAILURE.value)
        lockouts = sum(1 for e in all_events if e.event_type == SecurityEventType.ACCOUNT_LOCKED.value)
        cross_tenant_denials = sum(1 for e in all_events if e.event_type == SecurityEventType.CROSS_TENANT_ACCESS_DENIED.value)
        privilege_escalations = sum(1 for e in all_events if e.event_type == SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT.value)

        return {
            "period_days": days,
            "total_security_events": total_events,
            "critical_events": critical_events,
            "high_events": high_events,
            "failed_logins": failed_logins,
            "account_lockouts": lockouts,
            "cross_tenant_access_denials": cross_tenant_denials,
            "privilege_escalation_attempts": privilege_escalations,
        }

    @classmethod
    def list_events(
        cls,
        db: Session,
        tenant_id: Optional[UUID] = None,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SecurityEvent]:
        """Lists recent security events with filtering and pagination."""
        query = db.query(SecurityEvent)
        if tenant_id:
            query = query.filter(SecurityEvent.tenant_id == tenant_id)
        if severity:
            query = query.filter(SecurityEvent.severity == severity.upper())
        if event_type:
            query = query.filter(SecurityEvent.event_type == event_type.upper())

        return (
            query.order_by(desc(SecurityEvent.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )

