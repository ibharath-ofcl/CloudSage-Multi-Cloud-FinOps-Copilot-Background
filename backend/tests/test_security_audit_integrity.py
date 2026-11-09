"""
Stage 14 Test Suite: Tamper-Evident SHA-256 Audit Log Integrity & Governance.
Validates cryptographic hash chaining, secret redaction, tamper detection,
and immutable regulatory compliance checkpoints.
"""

from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.orm import Session

from backend.app.models.audit import AuditLog
from backend.app.security.audit_integrity import (
    AuditIntegrityService,
    compute_audit_hash,
    redact_secrets,
    GENESIS_HASH,
)


def test_redact_secrets_recursive_scrubbing():
    """Verify passwords, tokens, and sensitive keys are stripped recursively."""
    payload = {
        "user_email": "admin@enterprise.com",
        "password": "ClearTextPassword123!",
        "nested": {
            "api_key": "secret-key-abcdef",
            "token": "bearer-jwt-token-xyz",
            "safe_metric": 42.5,
        },
        "items": [
            {"secret": "sensitive-val"},
            {"public": "safe-val"},
        ],
    }

    sanitized = redact_secrets(payload)
    assert sanitized["user_email"] == "admin@enterprise.com"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_metric"] == 42.5
    assert sanitized["items"][0]["secret"] == "[REDACTED]"
    assert sanitized["items"][1]["public"] == "safe-val"


def test_compute_audit_hash_deterministic():
    """Verify hash computation is repeatable and deterministic for identical payloads."""
    now = datetime(2026, 11, 9, 12, 0, 0, tzinfo=timezone.utc)
    h1 = compute_audit_hash(
        previous_hash=GENESIS_HASH,
        timestamp=now,
        user_email="auditor@enterprise.com",
        action_type="LOGIN",
        resource_type="auth_sessions",
        resource_id="session-1",
        status="SUCCESS",
        before_state={"active": False},
        after_state={"active": True},
    )
    h2 = compute_audit_hash(
        previous_hash=GENESIS_HASH,
        timestamp=now,
        user_email="auditor@enterprise.com",
        action_type="LOGIN",
        resource_type="auth_sessions",
        resource_id="session-1",
        status="SUCCESS",
        before_state={"active": False},
        after_state={"active": True},
    )
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string


def test_compute_audit_hash_changes_on_tampering():
    """Verify changing any field yields completely different cryptographic hash."""
    now = datetime(2026, 11, 9, 12, 0, 0, tzinfo=timezone.utc)
    original_hash = compute_audit_hash(
        previous_hash=GENESIS_HASH,
        timestamp=now,
        user_email="auditor@enterprise.com",
        action_type="LOGIN",
        resource_type="auth_sessions",
        resource_id="session-1",
        status="SUCCESS",
    )
    tampered_hash = compute_audit_hash(
        previous_hash=GENESIS_HASH,
        timestamp=now,
        user_email="auditor@enterprise.com",
        action_type="LOGOUT",  # Modified action
        resource_type="auth_sessions",
        resource_id="session-1",
        status="SUCCESS",
    )
    assert original_hash != tampered_hash


def test_audit_record_chaining_sequential(db_session: Session):
    """Verify sequential audit records embed the previous record's hash."""
    user_id = uuid.uuid4()

    # Record 1 (Genesis predecessor)
    r1 = AuditIntegrityService.record_audit(
        db=db_session,
        user_id=user_id,
        user_email="user@enterprise.com",
        action_type="USER_CREATED",
        resource_type="users",
        resource_id=str(user_id),
        after_state={"email": "user@enterprise.com"},
    )
    assert r1.previous_hash == GENESIS_HASH
    assert r1.record_hash is not None

    # Record 2 (Linked to r1)
    r2 = AuditIntegrityService.record_audit(
        db=db_session,
        user_id=user_id,
        user_email="user@enterprise.com",
        action_type="ROLE_ASSIGNED",
        resource_type="user_roles",
        resource_id=str(user_id),
        before_state={"role": "VIEWER"},
        after_state={"role": "FINOPS_ANALYST"},
    )
    assert r2.previous_hash == r1.record_hash
    assert r2.record_hash != r1.record_hash

    # Record 3 (Linked to r2)
    r3 = AuditIntegrityService.record_audit(
        db=db_session,
        user_id=user_id,
        user_email="user@enterprise.com",
        action_type="SESSION_STARTED",
        resource_type="auth_sessions",
        resource_id="sess-123",
    )
    assert r3.previous_hash == r2.record_hash


def test_verify_chain_valid_on_unaltered_ledger(db_session: Session):
    """Verify verify_chain returns is_valid=True on legitimate audit log ledger."""
    for i in range(5):
        AuditIntegrityService.record_audit(
            db=db_session,
            user_id=uuid.uuid4(),
            user_email=f"user{i}@enterprise.com",
            action_type="API_CALL",
            resource_type="dashboards",
            resource_id=f"dash-{i}",
        )

    is_valid, count, err = AuditIntegrityService.verify_chain(db_session)
    assert is_valid is True
    assert count == 5
    assert err is None


def test_verify_chain_detects_record_tampering(db_session: Session):
    """Verify tampering with a record's after_state breaks chain verification."""
    # Create 3 records
    for i in range(3):
        AuditIntegrityService.record_audit(
            db=db_session,
            user_id=uuid.uuid4(),
            user_email=f"user{i}@enterprise.com",
            action_type="ACTION",
            resource_type="res",
            resource_id=f"id-{i}",
            after_state={"state": f"original_{i}"},
        )

    # Tamper with record #1 directly in database
    rec1 = db_session.query(AuditLog).order_by(AuditLog.timestamp.asc()).all()[1]
    rec1.after_state = {"state": "HACKED_TAMPERED_STATE"}
    db_session.commit()

    is_valid, count, err = AuditIntegrityService.verify_chain(db_session)
    assert is_valid is False
    assert err is not None
    assert "Hash mismatch" in err or "Chain broken" in err


def test_verify_chain_detects_record_deletion(db_session: Session):
    """Verify deleting an intermediate record breaks the previous_hash link."""
    # Create 4 records
    for i in range(4):
        AuditIntegrityService.record_audit(
            db=db_session,
            user_id=uuid.uuid4(),
            user_email=f"user{i}@enterprise.com",
            action_type="TRANSACTION",
            resource_type="orders",
            resource_id=f"order-{i}",
        )

    # Delete record #2
    records = db_session.query(AuditLog).order_by(AuditLog.timestamp.asc()).all()
    db_session.delete(records[2])
    db_session.commit()

    is_valid, count, err = AuditIntegrityService.verify_chain(db_session)
    assert is_valid is False
    assert err is not None
    assert "Chain broken" in err


def test_secret_redaction_in_audit_record(db_session: Session):
    """Verify passwords passed in before/after states are scrubbed before writing to database."""
    r = AuditIntegrityService.record_audit(
        db=db_session,
        user_id=uuid.uuid4(),
        user_email="admin@enterprise.com",
        action_type="PASSWORD_RESET",
        resource_type="users",
        resource_id="user-1",
        before_state={"old_password": "OldPlainPassword123!"},
        after_state={"new_password": "NewPlainPassword456!"},
    )

    # Inspect persisted record in database
    saved = db_session.query(AuditLog).filter(AuditLog.id == r.id).first()
    assert saved.before_state["old_password"] == "[REDACTED]"
    assert saved.after_state["new_password"] == "[REDACTED]"
    assert "OldPlainPassword123!" not in str(saved.before_state)


def test_create_integrity_checkpoint(db_session: Session):
    """Verify creating a checkpoint seals the audit log state into AuditIntegrityCheckpoint."""
    for i in range(3):
        AuditIntegrityService.record_audit(
            db=db_session,
            user_id=uuid.uuid4(),
            user_email=f"cp_user{i}@enterprise.com",
            action_type="EVENT",
            resource_type="system",
            resource_id=f"sys-{i}",
        )

    checkpoint = AuditIntegrityService.create_checkpoint(
        db=db_session,
        verified_by="auditor@external.audit",
    )
    assert checkpoint is not None
    assert checkpoint.is_valid is True
    assert checkpoint.record_count == 3
    assert checkpoint.verified_by == "auditor@external.audit"
    assert checkpoint.cumulative_hash is not None


def test_verify_chain_on_empty_ledger(db_session: Session):
    """Verify verify_chain returns is_valid=True when ledger is empty."""
    is_valid, count, err = AuditIntegrityService.verify_chain(db_session)
    assert is_valid is True
    assert count == 0
    assert err is None
