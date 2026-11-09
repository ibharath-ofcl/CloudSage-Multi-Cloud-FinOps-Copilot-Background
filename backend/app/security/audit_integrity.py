"""
CloudSage Tamper-Evident Audit Logging & Hash Integrity Service.
Implements:
- SHA-256 cryptographic hash chaining across consecutive audit ledger records.
- Secret and sensitive credential redaction.
- Non-repudiation verification and periodic integrity checkpoints.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.app.models.audit import AuditLog
from backend.app.models.security import AuditIntegrityCheckpoint

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

SENSITIVE_KEYS = {
    "password", "hashed_password", "token", "access_token", "refresh_token",
    "secret", "api_key", "secret_key", "authorization", "cookie"
}


def redact_secrets(data: Any) -> Any:
    """Recursively redacts passwords, tokens, and credentials from audit metadata."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = redact_secrets(v)
        return sanitized
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    return data


def compute_audit_hash(
    previous_hash: Optional[str],
    timestamp: datetime,
    user_email: Optional[str],
    action_type: str,
    resource_type: str,
    resource_id: Optional[str],
    status: str,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Computes deterministic SHA-256 hash for an audit record and its predecessor."""
    prev = previous_hash or GENESIS_HASH
    if timestamp:
        dt = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)
        ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        ts_str = ""
    user_str = user_email or "anonymous"
    res_id_str = resource_id or ""
    before_str = json.dumps(redact_secrets(before_state or {}), sort_keys=True)
    after_str = json.dumps(redact_secrets(after_state or {}), sort_keys=True)

    canonical_representation = (
        f"{prev}|{ts_str}|{user_str}|{action_type}|{resource_type}|"
        f"{res_id_str}|{status}|{before_str}|{after_str}"
    )
    return hashlib.sha256(canonical_representation.encode("utf-8")).hexdigest()


class AuditIntegrityService:
    """Manages tamper-evident cryptographic audit logs."""

    @classmethod
    def record_audit(
        cls,
        db: Session,
        user_id: Optional[UUID],
        user_email: Optional[str],
        action_type: str,
        resource_type: str,
        resource_id: Optional[str],
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
        status: str = "SUCCESS",
    ) -> AuditLog:
        """
        Appends an immutable audit log record linked to the previous record's hash.
        Redacts any secrets prior to persistence.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch latest audit record for previous hash in chain
        latest_record = (
            db.query(AuditLog)
            .order_by(desc(AuditLog.timestamp), desc(AuditLog.id))
            .first()
        )
        previous_hash = latest_record.record_hash if latest_record and latest_record.record_hash else GENESIS_HASH

        # 2. Sanitize payloads
        sanitized_before = redact_secrets(before_state) if before_state else None
        sanitized_after = redact_secrets(after_state) if after_state else None

        # 3. Compute hash
        record_hash = compute_audit_hash(
            previous_hash=previous_hash,
            timestamp=now,
            user_email=user_email,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            before_state=sanitized_before,
            after_state=sanitized_after,
        )

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            timestamp=now,
            user_id=user_id,
            tenant_id=tenant_id,
            user_email=user_email,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            before_state=sanitized_before,
            after_state=sanitized_after,
            client_ip=client_ip,
            status=status,
            previous_hash=previous_hash,
            record_hash=record_hash,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry

    @classmethod
    def verify_chain(
        cls,
        db: Session,
        limit: int = 1000,
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Validates SHA-256 cryptographic chain continuity across historical audit logs.
        Returns: (is_valid, records_verified, error_message)
        """
        records = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
            .limit(limit)
            .all()
        )

        if not records:
            return True, 0, None

        expected_prev = GENESIS_HASH
        for idx, rec in enumerate(records):
            if rec.previous_hash is not None and rec.previous_hash != expected_prev and idx > 0:
                # If first record has no previous hash (pre-Stage 14 legacy record), bootstrap chain
                if idx == 1 and records[0].previous_hash is None:
                    expected_prev = rec.record_hash
                    continue
                return False, idx, f"Chain broken at record #{rec.id}: expected prev {expected_prev}, found {rec.previous_hash}"

            if rec.record_hash is not None:
                computed = compute_audit_hash(
                    previous_hash=rec.previous_hash,
                    timestamp=rec.timestamp,
                    user_email=rec.user_email,
                    action_type=rec.action_type,
                    resource_type=rec.resource_type,
                    resource_id=rec.resource_id,
                    status=rec.status,
                    before_state=rec.before_state,
                    after_state=rec.after_state,
                )
                if computed != rec.record_hash:
                    return False, idx, f"Hash mismatch at record #{rec.id}: computed {computed}, found {rec.record_hash}"

            expected_prev = rec.record_hash or expected_prev

        return True, len(records), None

    @classmethod
    def create_checkpoint(
        cls,
        db: Session,
        tenant_id: Optional[UUID] = None,
        verified_by: str = "system@cloudsage.security",
    ) -> AuditIntegrityCheckpoint:
        """Runs chain verification and records an immutable checkpoint."""
        is_valid, count, err = cls.verify_chain(db)
        latest = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).first()
        last_id = latest.id if latest else uuid.uuid4()
        last_hash = latest.record_hash if latest and latest.record_hash else GENESIS_HASH

        checkpoint = AuditIntegrityCheckpoint(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            last_audit_id=last_id,
            cumulative_hash=last_hash,
            record_count=count,
            verified_by=verified_by,
            is_valid=is_valid,
            verified_at=datetime.now(timezone.utc),
        )
        db.add(checkpoint)
        db.commit()
        db.refresh(checkpoint)
        return checkpoint
