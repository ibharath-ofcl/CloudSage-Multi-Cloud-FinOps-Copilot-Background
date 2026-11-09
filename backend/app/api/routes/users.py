"""
CloudSage User Administration API Router.
Endpoints for user provisioning, role assignments, account lifecycle, and session revocation.
All operations require verified administrative permissions and enforce tenant boundaries.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.core.enums import AuditAction, SecurityEventType, UserRole
from backend.app.models.user import User
from backend.app.schemas.security import (
    CurrentUserResponse,
    RoleAssignmentRequest,
    UserCreateRequest,
    UserListItemResponse,
    UserListResponse,
    UserUpdateRequest,
)
from backend.app.security.audit_integrity import AuditIntegrityService
from backend.app.security.authorization import (
    get_current_principal,
    require_permission,
)
from backend.app.security.password_service import PasswordService
from backend.app.security.permissions import Permissions, get_permissions_for_roles
from backend.app.security.principals import AuthenticatedPrincipal
from backend.app.security.session_service import SessionService
from backend.app.security.tenant_context import TenantContext
from backend.app.security.threat_detection import ThreatDetectionService

router = APIRouter(prefix="/admin/users", tags=["User Administration"])


@router.get("", response_model=UserListResponse)
def list_users(
    tenant_id: Optional[UUID] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.USERS_READ)),
    db: Session = Depends(get_sync_db),
):
    """
    Lists platform users within authorized tenant scope.
    Supports filtering by role, active status, and search query.
    """
    # Enforce tenant isolation
    target_tenant = tenant_id or (UUID(str(principal.tenant_id)) if principal.tenant_id else None)
    TenantContext.verify_tenant_access(principal, target_tenant)

    query = db.query(User)
    query = TenantContext.scope_query(query, User, principal)

    if tenant_id and principal.is_super_admin:
        query = query.filter(User.tenant_id == tenant_id)
    if role:
        query = query.filter(User.role == role.upper())
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        pat = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(pat),
                User.full_name.ilike(pat),
                User.department.ilike(pat),
            )
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return UserListResponse(
        items=[UserListItemResponse.model_validate(u) for u in users],
        total=total,
    )


@router.post("", response_model=UserListItemResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user_in: UserCreateRequest,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.USERS_MANAGE)),
    db: Session = Depends(get_sync_db),
):
    """
    Provisions a new enterprise user.
    Enforces password complexity rules and prevents privilege escalation.
    """
    client_ip = request.client.host if request.client else "unknown"

    # 1. Tenant boundary
    target_tenant = user_in.tenant_id or (UUID(str(principal.tenant_id)) if principal.tenant_id else None)
    TenantContext.verify_tenant_access(principal, target_tenant)

    # 2. Check privilege escalation (only SUPER_ADMIN can create SUPER_ADMIN)
    target_role = user_in.role.upper()
    if target_role == UserRole.SUPER_ADMIN.value and not principal.is_super_admin:
        ThreatDetectionService.record_event(
            db=db,
            event_type=SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
            severity="HIGH",
            user_email=principal.email,
            user_id=UUID(principal.user_id) if principal.user_id else None,
            tenant_id=target_tenant,
            source_ip=client_ip,
            endpoint="/api/v1/admin/users",
            details={"attempted_role": target_role, "reason": "Non-superadmin cannot create SUPER_ADMIN"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can provision users with the SUPER_ADMIN role.",
        )

    # 3. Email uniqueness check
    clean_email = user_in.email.lower().strip()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{clean_email}' already exists.",
        )

    # 4. Password complexity validation
    is_valid_pwd, pwd_error = PasswordService.validate_password_strength(user_in.password)
    if not is_valid_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password does not meet complexity requirements: {pwd_error}",
        )

    # 5. Create user
    hashed_pwd = PasswordService.hash_password(user_in.password)
    new_user = User(
        id=uuid.uuid4(),
        tenant_id=target_tenant,
        email=clean_email,
        full_name=user_in.full_name.strip(),
        hashed_password=hashed_pwd,
        role=target_role,
        department=user_in.department,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 6. Audit log
    AuditIntegrityService.record_audit(
        db=db,
        user_id=UUID(principal.user_id) if principal.user_id else None,
        user_email=principal.email,
        action_type="USER_CREATE",
        resource_type="users",
        resource_id=str(new_user.id),
        before_state=None,
        after_state={"email": new_user.email, "role": new_user.role, "tenant_id": str(new_user.tenant_id)},
        tenant_id=target_tenant,
        client_ip=client_ip,
        status="SUCCESS",
    )

    return UserListItemResponse.model_validate(new_user)


@router.get("/{user_id}", response_model=CurrentUserResponse)
def get_user_detail(
    user_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.USERS_READ)),
    db: Session = Depends(get_sync_db),
):
    """Retrieves complete details for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    TenantContext.verify_tenant_access(principal, user.tenant_id)

    user_roles = [user.role]
    permissions = list(get_permissions_for_roles(user_roles))

    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        roles=user_roles,
        permissions=permissions,
        department=user.department,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        is_locked=user.is_locked,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.patch("/{user_id}", response_model=UserListItemResponse)
def update_user(
    request: Request,
    user_id: UUID,
    user_update: UserUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.USERS_MANAGE)),
    db: Session = Depends(get_sync_db),
):
    """
    Updates user profile, role, or active status.
    Prevents self-deactivation and unauthorized role escalation.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    TenantContext.verify_tenant_access(principal, user.tenant_id)
    client_ip = request.client.host if request.client else "unknown"

    # Self-protection rules:
    # 1. An admin cannot deactivate themselves
    if user_update.is_active is False and principal.user_id and str(user.id) == str(principal.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-deactivation is prohibited: An administrator cannot deactivate their own account.",
        )

    # 2. An admin cannot grant themselves SUPER_ADMIN
    if user_update.role:
        new_role = user_update.role.upper()
        if new_role == UserRole.SUPER_ADMIN.value and not principal.is_super_admin:
            ThreatDetectionService.record_event(
                db=db,
                event_type=SecurityEventType.PRIVILEGE_ESCALATION_ATTEMPT,
                severity="HIGH",
                user_email=principal.email,
                user_id=UUID(principal.user_id) if principal.user_id else None,
                tenant_id=user.tenant_id,
                source_ip=client_ip,
                endpoint=f"/api/v1/admin/users/{user_id}",
                details={"target_user": user.email, "attempted_role": new_role},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only SUPER_ADMIN can assign the SUPER_ADMIN role.",
            )

    before_state = {
        "full_name": user.full_name,
        "role": user.role,
        "department": user.department,
        "is_active": user.is_active,
    }

    if user_update.full_name is not None:
        user.full_name = user_update.full_name.strip()
    if user_update.role is not None:
        user.role = user_update.role.upper()
    if user_update.department is not None:
        user.department = user_update.department
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
        if not user.is_active:
            # If deactivating, immediately revoke all active sessions!
            SessionService.revoke_all_user_sessions(db, user.id, actor=f"admin:{principal.email}")

    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    AuditIntegrityService.record_audit(
        db=db,
        user_id=UUID(principal.user_id) if principal.user_id else None,
        user_email=principal.email,
        action_type="USER_UPDATE",
        resource_type="users",
        resource_id=str(user.id),
        before_state=before_state,
        after_state={
            "full_name": user.full_name,
            "role": user.role,
            "department": user.department,
            "is_active": user.is_active,
        },
        tenant_id=user.tenant_id,
        client_ip=client_ip,
        status="SUCCESS",
    )

    return UserListItemResponse.model_validate(user)


@router.post("/{user_id}/revoke-sessions", status_code=status.HTTP_200_OK)
def revoke_user_sessions(
    request: Request,
    user_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.SESSIONS_REVOKE)),
    db: Session = Depends(get_sync_db),
):
    """Revokes all active sessions for a target user immediately."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    TenantContext.verify_tenant_access(principal, user.tenant_id)
    revoked_count = SessionService.revoke_all_user_sessions(db, user.id, actor=principal.email)

    client_ip = request.client.host if request.client else "unknown"
    AuditIntegrityService.record_audit(
        db=db,
        user_id=UUID(principal.user_id) if principal.user_id else None,
        user_email=principal.email,
        action_type="SESSIONS_REVOKE",
        resource_type="users",
        resource_id=str(user.id),
        before_state=None,
        after_state={"revoked_sessions_count": revoked_count},
        tenant_id=user.tenant_id,
        client_ip=client_ip,
        status="SUCCESS",
    )

    return {"message": f"Successfully revoked {revoked_count} active session(s) for user {user.email}."}

