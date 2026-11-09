"""
CloudSage User Identity and Role Model.
Manages enterprise users, authentication credentials, and RBAC / ABAC scoping attributes.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from backend.app.core.database import Base
from backend.app.core.enums import UserRole


class User(Base):
    """Enterprise platform user with assigned RBAC role and departmental ABAC scope."""
    __tablename__ = "users"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    tenant_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Assigned enterprise organization / tenant ID"
    )
    email = Column(
        String(256),
        unique=True,
        nullable=False,
        index=True,
        doc="Corporate email address"
    )
    full_name = Column(
        String(128),
        nullable=False,
        doc="Full display name"
    )
    hashed_password = Column(
        String(256),
        nullable=False,
        doc="Argon2 or bcrypt password hash"
    )
    role = Column(
        String(32),
        nullable=False,
        default=UserRole.FINANCE_ANALYST.value,
        index=True,
        doc="Assigned primary RBAC role"
    )
    department = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Department or Squad for ABAC boundary scoping"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Active status indicator"
    )
    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Counter for consecutive failed password authentications"
    )
    is_locked = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether account is temporarily locked due to brute force"
    )
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp until which account is locked"
    )
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of most recent successful authentication"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Account provisioning timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Account profile update timestamp"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
