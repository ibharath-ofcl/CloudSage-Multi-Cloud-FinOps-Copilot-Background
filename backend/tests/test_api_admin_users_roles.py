"""
Stage 14 Test Suite: REST API Administration for Users, Roles & Permissions.
Validates /api/v1/admin/users and /api/v1/admin/roles endpoints,
self-deactivation prevention, privilege escalation protection, and session revocation.
"""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.core.enums import UserRole
from backend.app.main import app
from backend.app.models.user import User
from backend.app.security.authorization import get_current_principal
from backend.app.security.password_service import PasswordService
from backend.app.security.permissions import Permissions
from backend.app.security.principals import AuthenticatedPrincipal
from backend.app.security.session_service import SessionService


def _get_admin_principal(user_id=None, tenant_id=None, is_super_admin=False):
    return AuthenticatedPrincipal(
        email="orgadmin@enterprise.com",
        user_id=str(user_id or uuid.uuid4()),
        tenant_id=str(tenant_id or uuid.uuid4()),
        role=UserRole.SUPER_ADMIN.value if is_super_admin else UserRole.ORGANIZATION_ADMIN.value,
        permissions={
            Permissions.ALL if is_super_admin else Permissions.USERS_MANAGE,
            Permissions.USERS_READ,
            Permissions.USERS_MANAGE,
            Permissions.ROLES_READ,
            Permissions.SESSIONS_REVOKE,
        },
        is_authenticated=True,
        is_super_admin=is_super_admin,
    )


def test_api_list_users(db_session: Session):
    """Test GET /api/v1/admin/users lists users."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    u = User(
        email="dev1@enterprise.com",
        full_name="Developer One",
        hashed_password="some_hashed_pass",
        role=UserRole.CLOUD_ENGINEER.value,
        tenant_id=uuid.UUID(admin.tenant_id),
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    res = client.get("/api/v1/admin/users")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(i["email"] == "dev1@enterprise.com" for i in data["items"])

    app.dependency_overrides.clear()


def test_api_create_user_success(db_session: Session):
    """Test POST /api/v1/admin/users creates a new user."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    payload = {
        "email": "newbie@enterprise.com",
        "full_name": "New Hire",
        "password": "CompliantPassword#2026",
        "role": "FINOPS_ANALYST",
        "department": "Finance",
        "tenant_id": admin.tenant_id,
    }

    res = client.post("/api/v1/admin/users", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newbie@enterprise.com"
    assert data["role"] == "FINOPS_ANALYST"

    saved = db_session.query(User).filter(User.email == "newbie@enterprise.com").first()
    assert saved is not None
    assert PasswordService.verify_password("CompliantPassword#2026", saved.hashed_password) is True

    app.dependency_overrides.clear()


def test_api_create_user_duplicate_email_rejected(db_session: Session):
    """Test POST /api/v1/admin/users rejects duplicate email with 400."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    u = User(
        email="existing@enterprise.com",
        full_name="Existing User",
        hashed_password="some_hashed_pass",
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=uuid.UUID(admin.tenant_id),
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    payload = {
        "email": "existing@enterprise.com",
        "full_name": "Duplicate User",
        "password": "CompliantPassword#2026",
        "role": "VIEWER",
        "tenant_id": admin.tenant_id,
    }

    res = client.post("/api/v1/admin/users", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_api_create_user_prevents_privilege_escalation_to_super_admin(db_session: Session):
    """Verify non-superadmin cannot assign SUPER_ADMIN role (403 Forbidden)."""
    org_admin = _get_admin_principal(is_super_admin=False)
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: org_admin
    client = TestClient(app)

    payload = {
        "email": "escalate@enterprise.com",
        "full_name": "Escalation Candidate",
        "password": "CompliantPassword#2026",
        "role": "SUPER_ADMIN",
        "tenant_id": org_admin.tenant_id,
    }

    res = client.post("/api/v1/admin/users", json=payload)
    assert res.status_code == 403
    assert "only super_admin" in res.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_api_get_user_detail(db_session: Session):
    """Test GET /api/v1/admin/users/{id} returns details and mapped permissions."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    u = User(
        email="inspect@enterprise.com",
        full_name="Inspect User",
        hashed_password="some_hashed_pass",
        role=UserRole.FINOPS_MANAGER.value,
        tenant_id=uuid.UUID(admin.tenant_id),
        department="Operations",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    res = client.get(f"/api/v1/admin/users/{u.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "inspect@enterprise.com"
    assert data["role"] == UserRole.FINOPS_MANAGER.value
    assert "recommendations:approve" in data["permissions"]

    app.dependency_overrides.clear()


def test_api_update_user(db_session: Session):
    """Test PATCH /api/v1/admin/users/{id} updates attributes."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    u = User(
        email="modify@enterprise.com",
        full_name="Original Name",
        hashed_password="some_hashed_pass",
        role=UserRole.VIEWER.value,
        tenant_id=uuid.UUID(admin.tenant_id),
        department="General",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    update_payload = {
        "full_name": "Updated Name",
        "department": "Cloud FinOps Core",
        "role": "CLOUD_ENGINEER",
    }

    res = client.patch(f"/api/v1/admin/users/{u.id}", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Updated Name"
    assert data["role"] == "CLOUD_ENGINEER"

    app.dependency_overrides.clear()


def test_api_self_deactivation_prevention(db_session: Session):
    """Verify administrator is prevented from deactivating their own account (400 Bad Request)."""
    admin_id = uuid.uuid4()
    admin_user = User(
        id=admin_id,
        email="selfadmin@enterprise.com",
        full_name="Self Admin",
        hashed_password="some_hashed_pass",
        role=UserRole.ORGANIZATION_ADMIN.value,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()

    admin_principal = _get_admin_principal(user_id=admin_id)
    admin_principal.email = "selfadmin@enterprise.com"

    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin_principal
    client = TestClient(app)

    res = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"is_active": False},
    )
    assert res.status_code == 400
    assert "self-deactivation" in res.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_api_revoke_user_sessions(db_session: Session):
    """Test POST /api/v1/admin/users/{id}/revoke-sessions immediately revokes active sessions."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    u = User(
        email="active-sess@enterprise.com",
        full_name="Active Sessions User",
        hashed_password="some_hashed_pass",
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=uuid.UUID(admin.tenant_id),
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()

    # Create 2 sessions for this user
    SessionService.create_session(db_session, u)
    SessionService.create_session(db_session, u)

    res = client.post(f"/api/v1/admin/users/{u.id}/revoke-sessions")
    assert res.status_code == 200
    assert "revoked 2 active session" in res.json()["message"].lower()

    app.dependency_overrides.clear()


def test_api_list_roles(db_session: Session):
    """Test GET /api/v1/admin/roles lists all 7 enterprise roles."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    res = client.get("/api/v1/admin/roles")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 7
    role_names = [r["name"] for r in data["items"]]
    assert "SUPER_ADMIN" in role_names
    assert "FINOPS_MANAGER" in role_names
    assert "SECURITY_AUDITOR" in role_names

    app.dependency_overrides.clear()


def test_api_list_permissions_catalog(db_session: Session):
    """Test GET /api/v1/admin/roles/permissions lists all fine-grained permissions."""
    admin = _get_admin_principal()
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_principal] = lambda: admin
    client = TestClient(app)

    res = client.get("/api/v1/admin/roles/permissions")
    assert res.status_code == 200
    perms = res.json()
    assert isinstance(perms, list)
    assert len(perms) > 20
    assert "recommendations:approve" in perms
    assert "audit:read" in perms

    app.dependency_overrides.clear()

