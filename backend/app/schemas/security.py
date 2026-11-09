"""
CloudSage Security & Enterprise RBAC Pydantic Schemas.
Schemas for Authentication, Users, Roles, Permissions, Dual-Approval, and Threat Monitoring.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Authentication Schemas ---

class LoginRequest(BaseModel):
    email: str = Field(..., max_length=256)
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    department: Optional[str] = None
    tenant_id: Optional[UUID] = None
    is_active: bool
    is_locked: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: CurrentUserResponse


# --- User Administration Schemas ---

class UserCreateRequest(BaseModel):
    email: str = Field(..., max_length=256)
    full_name: str
    password: str
    role: str = "FINOPS_ANALYST"
    department: Optional[str] = None
    tenant_id: Optional[UUID] = None


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class UserListItemResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    tenant_id: Optional[UUID] = None
    is_active: bool
    is_locked: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: List[UserListItemResponse]
    total: int


class RoleAssignmentRequest(BaseModel):
    role: str
    justification: Optional[str] = None


# --- Role & Permission Schemas ---

class PermissionResponse(BaseModel):
    id: UUID
    name: str
    resource: str
    action: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RoleDetailResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    items: List[RoleDetailResponse]
    total: int


class RoleCreateRequest(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


# --- Dual Approval Schemas ---

class ApprovalRequestCreate(BaseModel):
    action_type: str
    resource_type: str
    resource_id: str
    requested_payload: Dict[str, Any] = Field(default_factory=dict)
    justification: str


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    decision_notes: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    requester_email: str
    action_type: str
    resource_type: str
    resource_id: str
    requested_payload: Dict[str, Any]
    justification: str
    status: str
    approver_email: Optional[str] = None
    decision_notes: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    decided_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Security Events & Audit Checkpoint Schemas ---

class SecurityEventResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    user_email: Optional[str] = None
    event_type: str
    severity: str
    source_ip: Optional[str] = None
    endpoint: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityStatsResponse(BaseModel):
    period_days: int
    total_security_events: int
    critical_events: int
    high_events: int
    failed_logins: int
    account_lockouts: int
    cross_tenant_access_denials: int
    privilege_escalation_attempts: int


class AuditVerificationResponse(BaseModel):
    is_valid: bool
    records_verified: int
    error_message: Optional[str] = None
    verified_at: datetime
