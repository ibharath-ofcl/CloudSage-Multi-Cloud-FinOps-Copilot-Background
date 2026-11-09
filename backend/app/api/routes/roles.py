"""
CloudSage Role & Permission Administration API Router.
Provides inspection of the 7 enterprise roles and granular permission matrix.
"""

from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.enums import UserRole
from backend.app.schemas.security import (
    PermissionResponse,
    RoleDetailResponse,
    RoleListResponse,
)
from backend.app.security.authorization import require_permission
from backend.app.security.permissions import (
    ALL_PERMISSIONS,
    Permissions,
    ROLE_PERMISSIONS_MAP,
    get_permissions_for_role,
)
from backend.app.security.principals import AuthenticatedPrincipal

router = APIRouter(prefix="/admin/roles", tags=["Role & Permission Administration"])

ROLE_METADATA = {
    UserRole.SUPER_ADMIN.value: {
        "display_name": "Super Administrator",
        "description": "Global platform superuser with unrestricted platform-wide authority, cross-tenant management, and security administration.",
    },
    UserRole.ORGANIZATION_ADMIN.value: {
        "display_name": "Organization Administrator",
        "description": "Tenant administrator managing users, cloud accounts, integrations, alert rules, and security policies within the organization.",
    },
    UserRole.FINOPS_MANAGER.value: {
        "display_name": "FinOps Manager",
        "description": "Financial operations lead with authority to approve recommendations, assign investigations, manage alert rules, and review org-wide spend.",
    },
    UserRole.FINOPS_ANALYST.value: {
        "display_name": "FinOps Analyst",
        "description": "Financial analyst analyzing cost trends, triaging anomalies, authoring investigation findings, and evaluating waste opportunities.",
    },
    UserRole.CLOUD_ENGINEER.value: {
        "display_name": "Cloud Engineer",
        "description": "Technical engineer inspecting cloud resource telemetry, reviewing hardware metrics, and contributing root cause evidence.",
    },
    UserRole.SECURITY_AUDITOR.value: {
        "display_name": "Security Auditor",
        "description": "Read-only compliance auditor inspecting audit logs, security events, authentication records, and hash chain integrity.",
    },
    UserRole.VIEWER.value: {
        "display_name": "Read-Only Viewer",
        "description": "Read-only access to authorized high-level dashboards and summaries.",
    },
}


@router.get("", response_model=RoleListResponse)
def list_roles(
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.ROLES_READ)),
):
    """Lists the 7 canonical enterprise RBAC roles and their associated permissions."""
    items: List[RoleDetailResponse] = []
    for role_name, meta in ROLE_METADATA.items():
        perms = list(get_permissions_for_role(role_name))
        items.append(
            RoleDetailResponse(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, role_name),
                name=role_name,
                display_name=meta["display_name"],
                description=meta["description"],
                is_system_role=True,
                permissions=perms,
            )
        )

    return RoleListResponse(items=items, total=len(items))


@router.get("/permissions", response_model=List[str])
@router.get("/permissions/all", response_model=List[str])
def list_all_permissions(
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.ROLES_READ)),
):
    """Lists all available fine-grained permission codes."""
    return sorted(ALL_PERMISSIONS)


@router.get("/{role_name}", response_model=RoleDetailResponse)
def get_role_detail(
    role_name: str,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.ROLES_READ)),
):
    """Retrieves full permission matrix details for a specific role."""
    canonical_name = role_name.upper()
    if canonical_name not in ROLE_METADATA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found.",
        )

    meta = ROLE_METADATA[canonical_name]
    perms = list(get_permissions_for_role(canonical_name))

    return RoleDetailResponse(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, canonical_name),
        name=canonical_name,
        display_name=meta["display_name"],
        description=meta["description"],
        is_system_role=True,
        permissions=perms,
    )
