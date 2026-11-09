"""
CloudSage Enterprise Security & RBAC Data Models.
Implements:
- Multi-Tenant Organizations (Tenant)
- Role-Based Access Control (Role, Permission, RolePermission, UserRoleMapping)
- Session Management & Token Revocation (UserSession)
- Dual Approval & Separation of Duties (ApprovalRequest)
- Security Monitoring & Threat Detection (SecurityEvent)
- Audit Hash Integrity Checkpoints (AuditIntegrityCheckpoint)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from backend.app.core.database import Base
from backend.app.core.enums import (
    ApprovalStatus,
    SecurityEventSeverity,
    SecurityEventType,
    SessionStatus,
    UserRole,
)

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Tenant(Base):
    """
    Enterprise Tenant / Organization entity.
    Provides strict cryptographic and logical boundaries across multi-cloud accounts and billing.
    """
    __tablename__ = "tenants"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        doc="Human-readable Organization name",
    )
    slug = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        doc="URL-friendly identifier",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether organization access is active",
    )
    security_policy = Column(
        JSON_TYPE,
        nullable=False,
        default=lambda: {
            "require_dual_approval": True,
            "max_session_duration_minutes": 1440,
            "session_inactivity_timeout_minutes": 60,
            "ip_allowlist": [],
            "mfa_enforced": False,
        },
        doc="Tenant-specific security policies",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name} slug={self.slug}>"


class Permission(Base):
    """Fine-grained permission (resource:action)."""
    __tablename__ = "permissions"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        doc="Permission code (e.g., billing:read, recommendations:approve)",
    )
    resource = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Target resource namespace (billing, waste, users)",
    )
    action = Column(
        String(64),
        nullable=False,
        doc="Permitted operation (read, update, approve, delete)",
    )
    description = Column(
        String(256),
        nullable=True,
        doc="Functional description of this capability",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Permission name={self.name}>"


# Association table linking roles to permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """Configurable and system RBAC role."""
    __tablename__ = "roles"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        doc="Role name (e.g. SUPER_ADMIN, FINOPS_MANAGER, SECURITY_AUDITOR)",
    )
    display_name = Column(
        String(128),
        nullable=False,
        doc="User-friendly role title",
    )
    description = Column(
        String(512),
        nullable=True,
        doc="Role responsibilities and access boundaries",
    )
    is_system_role = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether role is a built-in immutable system role",
    )
    tenant_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Null for global system roles; populated for custom tenant roles",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    permissions = relationship("Permission", secondary=role_permissions, lazy="selectin")

    def __repr__(self) -> str:
        return f"<Role name={self.name} is_system={self.is_system_role}>"


class UserRoleMapping(Base):
    """Maps a user to one or more roles with assignment provenance."""
    __tablename__ = "user_role_mappings"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by = Column(
        String(256),
        nullable=False,
        doc="Actor email who granted this role",
    )
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_user_role_unique", "user_id", "role_id", unique=True),
    )


class UserSession(Base):
    """
    Active authenticated user session tracking for revocation and concurrency control.
    """
    __tablename__ = "user_sessions"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_jti = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique JWT Token ID",
    )
    refresh_token_hash = Column(
        String(64),
        nullable=True,
        index=True,
        doc="SHA-256 hash of active refresh token",
    )
    client_ip = Column(
        String(64),
        nullable=True,
    )
    user_agent = Column(
        String(512),
        nullable=True,
    )
    status = Column(
        String(16),
        nullable=False,
        default=SessionStatus.ACTIVE.value,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by = Column(
        String(256),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user={self.user_id} status={self.status}>"


class ApprovalRequest(Base):
    """
    Multi-Party Governance / Dual Approval for sensitive administrative operations.
    Enforces separation of duties (requester != approver).
    """
    __tablename__ = "approval_requests"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    tenant_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    requester_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_email = Column(
        String(256),
        nullable=False,
    )
    action_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Privileged action (e.g. ASSIGN_SUPER_ADMIN, UPDATE_SECURITY_POLICY, EXPORT_TENANT_DATA)",
    )
    resource_type = Column(
        String(64),
        nullable=False,
        doc="Target entity type",
    )
    resource_id = Column(
        String(512),
        nullable=False,
        doc="Target entity ID",
    )
    requested_payload = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Requested mutation payload awaiting review",
    )
    justification = Column(
        Text,
        nullable=False,
        doc="Business rationale supplied by requester",
    )
    status = Column(
        String(32),
        nullable=False,
        default=ApprovalStatus.PENDING.value,
        index=True,
    )
    approver_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approver_email = Column(
        String(256),
        nullable=True,
    )
    decision_notes = Column(
        Text,
        nullable=True,
        doc="Comments from independent approver",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Expiration timestamp for pending request",
    )
    decided_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest id={self.id} action={self.action_type} status={self.status}>"


class SecurityEvent(Base):
    """
    Security monitoring and intrusion detection events.
    Tracks brute-force attempts, cross-tenant probing, privilege escalation, and token anomalies.
    """
    __tablename__ = "security_events"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    tenant_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email = Column(
        String(256),
        nullable=True,
        index=True,
    )
    event_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Type from SecurityEventType (e.g. LOGIN_FAILURE, CROSS_TENANT_ACCESS_DENIED)",
    )
    severity = Column(
        String(16),
        nullable=False,
        default=SecurityEventSeverity.MEDIUM.value,
        index=True,
    )
    source_ip = Column(
        String(64),
        nullable=True,
        index=True,
    )
    endpoint = Column(
        String(256),
        nullable=True,
    )
    details = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Sanitized event telemetry (never contains secrets/passwords)",
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("idx_sec_event_type_time", "event_type", "timestamp"),
        Index("idx_sec_event_ip_time", "source_ip", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<SecurityEvent type={self.event_type} severity={self.severity} ip={self.source_ip}>"


class AuditIntegrityCheckpoint(Base):
    """
    Periodic cryptographic audit checkpoints verifying SHA-256 hash chains.
    Enforces non-repudiation and detects unauthorized row alterations.
    """
    __tablename__ = "audit_integrity_checkpoints"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    tenant_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    last_audit_id = Column(
        Uuid(as_uuid=True),
        nullable=False,
        doc="ID of the latest audit record included in this checkpoint",
    )
    cumulative_hash = Column(
        String(64),
        nullable=False,
        doc="Cumulative SHA-256 hash of the audit chain up to last_audit_id",
    )
    record_count = Column(
        Integer,
        nullable=False,
        doc="Number of audit records verified in this checkpoint",
    )
    verified_by = Column(
        String(256),
        nullable=False,
        default="system@cloudsage.security",
    )
    is_valid = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="True if chain verified intact; False if hash mismatch detected",
    )
    verified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AuditIntegrityCheckpoint id={self.id} count={self.record_count} valid={self.is_valid}>"

