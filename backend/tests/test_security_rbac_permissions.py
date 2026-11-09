"""
Stage 14 Test Suite: Enterprise RBAC & Fine-Grained Permission Enforcement.
Validates 7 canonical enterprise roles, backward-compatible aliases,
wildcard superadmin resolution, and FastAPI permission gate dependencies.
"""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app.core.database import get_sync_db
from backend.app.core.enums import UserRole
from backend.app.security.authorization import (
    get_current_principal,
    require_permission,
    require_role,
    require_super_admin,
)
from backend.app.security.permissions import (
    Permissions,
    ROLE_PERMISSIONS_MAP,
    get_permissions_for_role,
    get_permissions_for_roles,
    has_permission,
)
from backend.app.security.principals import AuthenticatedPrincipal


def test_seven_enterprise_roles_defined_in_enum():
    """Verify all 7 enterprise roles exist in the UserRole enum."""
    expected_roles = {
        "SUPER_ADMIN",
        "ORGANIZATION_ADMIN",
        "FINOPS_MANAGER",
        "FINOPS_ANALYST",
        "CLOUD_ENGINEER",
        "SECURITY_AUDITOR",
        "VIEWER",
    }
    actual_roles = {r.value for r in UserRole}
    for role in expected_roles:
        assert role in actual_roles, f"Role {role} missing from UserRole enum"


def test_backward_compatible_aliases_resolve_permissions():
    """Verify legacy aliases correctly resolve to active permission sets."""
    aliases = [
        UserRole.FINOPS_ENGINEER.value,
        UserRole.FINANCE_ANALYST.value,
        UserRole.ENGINEERING_MANAGER.value,
        UserRole.EXECUTIVE.value,
    ]
    for alias in aliases:
        perms = get_permissions_for_role(alias)
        assert len(perms) > 0, f"Alias {alias} resolved to empty permissions"
        assert Permissions.DASHBOARD_READ in perms


def test_super_admin_has_wildcard_authority():
    """Verify SUPER_ADMIN possesses wildcard '*' permission and can perform any action."""
    perms = get_permissions_for_role(UserRole.SUPER_ADMIN.value)
    assert Permissions.ALL in perms
    assert has_permission(perms, "any:arbitrary_action") is True
    assert has_permission(perms, Permissions.USERS_MANAGE) is True
    assert has_permission(perms, Permissions.SECURITY_MANAGE) is True


def test_organization_admin_permissions():
    """Verify ORGANIZATION_ADMIN has user/role governance but lacks wildcard."""
    perms = get_permissions_for_role(UserRole.ORGANIZATION_ADMIN.value)
    assert Permissions.ALL not in perms
    assert Permissions.USERS_READ in perms
    assert Permissions.USERS_MANAGE in perms
    assert Permissions.ROLES_READ in perms
    assert Permissions.DASHBOARD_READ in perms


def test_finops_manager_permissions():
    """Verify FINOPS_MANAGER can approve recommendations and manage rules."""
    perms = get_permissions_for_role(UserRole.FINOPS_MANAGER.value)
    assert Permissions.RECOMMENDATIONS_APPROVE in perms
    assert Permissions.NOTIFICATION_RULES_MANAGE in perms
    assert Permissions.INVESTIGATIONS_CLOSE in perms
    assert Permissions.ALERTS_ACKNOWLEDGE in perms
    assert Permissions.USERS_MANAGE not in perms


def test_finops_analyst_permissions():
    """Verify FINOPS_ANALYST can analyze anomalies and create drafts, but cannot approve."""
    perms = get_permissions_for_role(UserRole.FINOPS_ANALYST.value)
    assert Permissions.ANOMALIES_READ in perms
    assert Permissions.INVESTIGATIONS_CREATE in perms
    assert Permissions.RECOMMENDATIONS_READ in perms
    # Must NOT have approve authority
    assert Permissions.RECOMMENDATIONS_APPROVE not in perms
    assert Permissions.USERS_MANAGE not in perms


def test_cloud_engineer_permissions():
    """Verify CLOUD_ENGINEER can view inventory and waste, but cannot approve or manage users."""
    perms = get_permissions_for_role(UserRole.CLOUD_ENGINEER.value)
    assert Permissions.RESOURCES_READ in perms
    assert Permissions.WASTE_READ in perms
    assert Permissions.DASHBOARD_READ in perms
    # Cannot manage users or approve alerts
    assert Permissions.USERS_MANAGE not in perms
    assert Permissions.NOTIFICATION_RULES_MANAGE not in perms


def test_security_auditor_permissions():
    """Verify SECURITY_AUDITOR has read access to audit logs and security, cannot mutate."""
    perms = get_permissions_for_role(UserRole.SECURITY_AUDITOR.value)
    assert Permissions.AUDIT_READ in perms
    assert Permissions.AUDIT_VERIFY in perms
    assert Permissions.SECURITY_READ in perms
    assert Permissions.USERS_READ in perms
    # Cannot modify FinOps data
    assert Permissions.RECOMMENDATIONS_APPROVE not in perms
    assert Permissions.USERS_MANAGE not in perms


def test_viewer_is_strictly_read_only():
    """Verify VIEWER role has only read capabilities for dashboards and billing."""
    perms = get_permissions_for_role(UserRole.VIEWER.value)
    assert Permissions.DASHBOARD_READ in perms
    assert Permissions.BILLING_READ in perms
    # Strictly no mutation or approvals
    assert Permissions.RECOMMENDATIONS_APPROVE not in perms
    assert Permissions.INVESTIGATIONS_CREATE not in perms
    assert Permissions.USERS_MANAGE not in perms


def test_multi_role_permission_aggregation():
    """Verify assigning multiple roles properly merges union of permissions."""
    combined = get_permissions_for_roles([UserRole.VIEWER.value, UserRole.CLOUD_ENGINEER.value])
    assert Permissions.DASHBOARD_READ in combined
    assert Permissions.RESOURCES_READ in combined
    assert Permissions.WASTE_READ in combined


def test_require_permission_fastapi_dependency(db_session):
    """Verify require_permission dependency permits authorized principal and denies unauthorized with 403."""
    test_app = FastAPI()

    perm_dep = require_permission(Permissions.RECOMMENDATIONS_APPROVE)

    @test_app.get("/guarded-action")
    def guarded_endpoint(
        principal: AuthenticatedPrincipal = Depends(perm_dep),
    ):
        return {"status": "ok", "user": principal.email}

    test_app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(test_app)

    # 1. Authorized manager
    test_app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        email="manager@enterprise.com",
        role=UserRole.FINOPS_MANAGER.value,
        permissions={Permissions.RECOMMENDATIONS_APPROVE},
        is_authenticated=True,
    )
    res = client.get("/guarded-action")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Unauthorized analyst (lacks RECOMMENDATIONS_APPROVE)
    test_app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        email="analyst@enterprise.com",
        role=UserRole.FINOPS_ANALYST.value,
        permissions={Permissions.ANOMALIES_READ},
        is_authenticated=True,
    )
    denied_res = client.get("/guarded-action")
    assert denied_res.status_code == 403


def test_require_role_fastapi_dependency(db_session):
    """Verify require_role dependency enforces allowed role boundaries."""
    test_app = FastAPI()

    role_dep = require_role(UserRole.SUPER_ADMIN.value, UserRole.ORGANIZATION_ADMIN.value)

    @test_app.get("/admin-only")
    def admin_endpoint(
        principal: AuthenticatedPrincipal = Depends(role_dep),
    ):
        return {"admin": True}

    test_app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(test_app)

    # 1. Allowed role: ORGANIZATION_ADMIN
    test_app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        email="orgadmin@enterprise.com",
        role=UserRole.ORGANIZATION_ADMIN.value,
        roles=[UserRole.ORGANIZATION_ADMIN.value],
        is_authenticated=True,
    )
    res = client.get("/admin-only")
    assert res.status_code == 200

    # 2. Denied role: VIEWER
    test_app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        email="viewer@enterprise.com",
        role=UserRole.VIEWER.value,
        roles=[UserRole.VIEWER.value],
        is_authenticated=True,
    )
    denied = client.get("/admin-only")
    assert denied.status_code == 403
