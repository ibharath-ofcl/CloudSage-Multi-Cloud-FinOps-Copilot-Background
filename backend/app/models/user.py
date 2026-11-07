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
    Index,
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
        doc="Assigned RBAC role"
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
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Account provisioning timestamp"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
