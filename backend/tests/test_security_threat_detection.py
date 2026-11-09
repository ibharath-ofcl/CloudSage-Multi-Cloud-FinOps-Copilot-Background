"""
Stage 14 Test Suite: Threat Detection, Brute-Force Lockouts & Security Telemetry.
Validates failed login tracking, automatic account lockout thresholds,
threat event logging, severity ratings, and security posture statistics.
"""

from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.enums import SecurityEventSeverity, SecurityEventType, UserRole
from backend.app.models.security import SecurityEvent
from backend.app.models.user import User
from backend.app.security.threat_detection import ThreatDetectionService


def test_handle_failed_login_increments_counter(db_session: Session):
    """Verify failed login attempts increment counter on user record."""
    user = User(
        email="target@enterprise.com",
        full_name="Target User",
        hashed_password="some_hashed_password",
        role=UserRole.VIEWER.value,
        failed_login_attempts=0,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    ThreatDetectionService.handle_failed_login(
        db=db_session,
        email="target@enterprise.com",
        source_ip="192.168.1.100",
    )

    db_session.refresh(user)
    assert user.failed_login_attempts == 1
    assert user.is_locked is False


def test_brute_force_triggers_account_lockout(db_session: Session):
    """Verify reaching LOGIN_MAX_FAILED_ATTEMPTS locks account and logs CRITICAL event."""
    user = User(
        email="brute_force_target@enterprise.com",
        full_name="Target User",
        hashed_password="some_hashed_password",
        role=UserRole.VIEWER.value,
        failed_login_attempts=settings.LOGIN_MAX_FAILED_ATTEMPTS - 1,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Next failure hits threshold
    ThreatDetectionService.handle_failed_login(
        db=db_session,
        email="brute_force_target@enterprise.com",
        source_ip="10.0.0.99",
    )

    db_session.refresh(user)
    assert user.is_locked is True
    assert user.locked_until is not None

    # Verify CRITICAL security event was recorded
    events = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.user_email == "brute_force_target@enterprise.com")
        .all()
    )
    assert any(e.event_type == SecurityEventType.ACCOUNT_LOCKED.value for e in events)


def test_handle_successful_login_resets_counter(db_session: Session):
    """Verify successful login resets failed_login_attempts to zero and updates last_login_at."""
    user = User(
        email="success_user@enterprise.com",
        full_name="Success User",
        hashed_password="some_hashed_password",
        role=UserRole.FINOPS_ANALYST.value,
        failed_login_attempts=3,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    ThreatDetectionService.handle_successful_login(
        db=db_session,
        user=user,
        source_ip="127.0.0.1",
    )

    db_session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.is_locked is False
    assert user.last_login_at is not None


def test_record_security_event_all_severities(db_session: Session):
    """Verify security events can be logged across all 5 severity levels."""
    severities = [
        SecurityEventSeverity.CRITICAL,
        SecurityEventSeverity.HIGH,
        SecurityEventSeverity.MEDIUM,
        SecurityEventSeverity.LOW,
        SecurityEventSeverity.INFORMATIONAL,
    ]

    for sev in severities:
        ev = ThreatDetectionService.record_event(
            db=db_session,
            event_type=SecurityEventType.LOGIN_SUCCESS,
            severity=sev,
            user_email="auditor@enterprise.com",
            details={"test_severity": sev.value},
        )
        assert ev.severity == sev.value

    count = db_session.query(SecurityEvent).count()
    assert count == 5


def test_privilege_escalation_event_logging(db_session: Session):
    """Verify privilege escalation attempt is logged with HIGH severity."""
    ev = ThreatDetectionService.record_event(
        db=db_session,
        event_type=SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
        severity=SecurityEventSeverity.HIGH,
        user_email="attacker@enterprise.com",
        details={"attempted_role": "SUPER_ADMIN", "current_role": "VIEWER"},
    )

    assert ev.event_type == SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT.value
    assert ev.severity == SecurityEventSeverity.HIGH.value
    assert ev.details["attempted_role"] == "SUPER_ADMIN"


def test_cross_tenant_access_denied_event_logging(db_session: Session):
    """Verify cross-tenant access violation logs appropriate event."""
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()

    ev = ThreatDetectionService.record_event(
        db=db_session,
        event_type=SecurityEventType.CROSS_TENANT_ACCESS_DENIED,
        severity=SecurityEventSeverity.HIGH,
        tenant_id=t1,
        user_email="prober@tenant1.com",
        details={"target_tenant_id": str(t2)},
    )

    assert ev.event_type == SecurityEventType.CROSS_TENANT_ACCESS_DENIED.value
    assert ev.tenant_id == t1


def test_list_events_with_filters(db_session: Session):
    """Verify list_events filters by severity, event_type, and pagination."""
    for i in range(10):
        sev = SecurityEventSeverity.CRITICAL if i % 2 == 0 else SecurityEventSeverity.LOW
        evt = SecurityEventType.LOGIN_FAILURE if i % 2 == 0 else SecurityEventType.LOGIN_SUCCESS
        ThreatDetectionService.record_event(
            db=db_session,
            event_type=evt,
            severity=sev,
            user_email=f"user_{i}@enterprise.com",
        )

    # Filter by CRITICAL
    crit_events = ThreatDetectionService.list_events(
        db=db_session,
        severity="CRITICAL",
    )
    assert len(crit_events) == 5
    assert all(e.severity == "CRITICAL" for e in crit_events)

    # Filter by event_type
    login_successes = ThreatDetectionService.list_events(
        db=db_session,
        event_type="LOGIN_SUCCESS",
    )
    assert len(login_successes) == 5

    # Pagination: limit 3
    page_1 = ThreatDetectionService.list_events(db=db_session, limit=3, offset=0)
    assert len(page_1) == 3


def test_get_security_stats_aggregation(db_session: Session):
    """Verify get_security_stats correctly tallies event counts and critical alerts."""
    # Seed various events
    ThreatDetectionService.record_event(
        db=db_session,
        event_type=SecurityEventType.ACCOUNT_LOCKED,
        severity=SecurityEventSeverity.CRITICAL,
        user_email="victim@enterprise.com",
    )
    ThreatDetectionService.record_event(
        db=db_session,
        event_type=SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
        severity=SecurityEventSeverity.HIGH,
        user_email="hacker@enterprise.com",
    )
    ThreatDetectionService.record_event(
        db=db_session,
        event_type=SecurityEventType.LOGIN_FAILURE,
        severity=SecurityEventSeverity.MEDIUM,
        user_email="victim@enterprise.com",
    )
    ThreatDetectionService.record_event(
        db=db_session,
        event_type=SecurityEventType.CROSS_TENANT_ACCESS_DENIED,
        severity=SecurityEventSeverity.HIGH,
        user_email="prober@enterprise.com",
    )

    stats = ThreatDetectionService.get_security_stats(db=db_session, days=7)
    assert stats["total_security_events"] == 4
    assert stats["critical_events"] == 1
    assert stats["high_events"] == 2
    assert stats["account_lockouts"] == 1
    assert stats["privilege_escalation_attempts"] == 1
    assert stats["cross_tenant_access_denials"] == 1


def test_failed_login_for_non_existent_user(db_session: Session):
    """Verify failed login attempt for unregistered email logs event without error."""
    ThreatDetectionService.handle_failed_login(
        db=db_session,
        email="ghost_non_existent@enterprise.com",
        source_ip="192.0.2.1",
    )

    events = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.user_email == "ghost_non_existent@enterprise.com")
        .all()
    )
    assert len(events) == 1
    assert events[0].event_type == SecurityEventType.LOGIN_FAILURE.value


def test_empty_security_stats_returns_zeroes(db_session: Session):
    """Verify clean database returns zero counts without error."""
    stats = ThreatDetectionService.get_security_stats(db=db_session, days=1)
    assert stats["total_security_events"] == 0
    assert stats["critical_events"] == 0
    assert stats["account_lockouts"] == 0
