"""
Stage 14 Test Suite: Multi-Tenant Data Isolation & IDOR Protection.
Validates Tenant model lifecycle, query scoping, cross-tenant rejection,
and superadmin global bypass authority.
"""

import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.core.enums import UserRole
from backend.app.models.security import Tenant, SecurityEvent
from backend.app.models.user import User
from backend.app.security.principals import AuthenticatedPrincipal
from backend.app.security.tenant_context import TenantContext


def test_tenant_model_creation(db_session: Session):
    """Verify Tenant records can be created with unique slugs and names."""
    t1 = Tenant(
        id=uuid.uuid4(),
        name="Acme Corporation",
        slug="acme-corp",
        is_active=True,
    )
    db_session.add(t1)
    db_session.commit()

    saved = db_session.query(Tenant).filter(Tenant.slug == "acme-corp").first()
    assert saved is not None
    assert saved.name == "Acme Corporation"
    assert saved.is_active is True


def test_tenant_context_verify_same_tenant_permitted():
    """Verify principal can access resources belonging to their own tenant."""
    tenant_id = uuid.uuid4()
    principal = AuthenticatedPrincipal(
        email="user@acme.com",
        tenant_id=str(tenant_id),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )

    # Should not raise exception
    TenantContext.verify_tenant_access(principal, target_tenant_id=tenant_id)


def test_tenant_context_verify_cross_tenant_denied():
    """Verify principal attempting to access another tenant raises 403 Forbidden."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    principal = AuthenticatedPrincipal(
        email="user@tenant-a.com",
        tenant_id=str(tenant_a),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        TenantContext.verify_tenant_access(principal, target_tenant_id=tenant_b)
    assert exc_info.value.status_code == 403
    assert "cross-tenant" in exc_info.value.detail.lower()


def test_super_admin_bypasses_tenant_isolation():
    """Verify SUPER_ADMIN possesses global cross-tenant inspection authority."""
    tenant_any = uuid.uuid4()
    superadmin = AuthenticatedPrincipal(
        email="superadmin@cloudsage.internal",
        tenant_id=None,
        role=UserRole.SUPER_ADMIN.value,
        is_authenticated=True,
        is_super_admin=True,
    )

    # Must NOT raise exception
    TenantContext.verify_tenant_access(superadmin, target_tenant_id=tenant_any)


def test_query_scoping_filters_records_to_principal_tenant(db_session: Session):
    """Verify scope_query isolates database results strictly to principal's tenant."""
    tenant_1 = uuid.uuid4()
    tenant_2 = uuid.uuid4()

    u1 = User(
        email="u1@tenant1.com",
        full_name="User One",
        hashed_password="hashed_pass_1",
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=tenant_1,
        is_active=True,
    )
    u2 = User(
        email="u2@tenant2.com",
        full_name="User Two",
        hashed_password="hashed_pass_2",
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=tenant_2,
        is_active=True,
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    principal_1 = AuthenticatedPrincipal(
        email="u1@tenant1.com",
        tenant_id=str(tenant_1),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )

    base_query = db_session.query(User)
    scoped_query = TenantContext.scope_query(base_query, User, principal_1)
    results = scoped_query.all()

    assert len(results) == 1
    assert results[0].email == "u1@tenant1.com"
    assert results[0].tenant_id == tenant_1


def test_query_scoping_super_admin_sees_all_tenants(db_session: Session):
    """Verify SUPER_ADMIN receives unscoped query results covering all tenants."""
    tenant_1 = uuid.uuid4()
    tenant_2 = uuid.uuid4()

    u1 = User(
        email="alpha@t1.com",
        full_name="Alpha",
        hashed_password="hashed_pass_1",
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=tenant_1,
        is_active=True,
    )
    u2 = User(
        email="beta@t2.com",
        full_name="Beta",
        hashed_password="hashed_pass_2",
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=tenant_2,
        is_active=True,
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    superadmin = AuthenticatedPrincipal(
        email="root@cloudsage.internal",
        role=UserRole.SUPER_ADMIN.value,
        is_authenticated=True,
        is_super_admin=True,
    )

    base_query = db_session.query(User)
    scoped_query = TenantContext.scope_query(base_query, User, superadmin)
    results = scoped_query.all()

    assert len(results) >= 2


def test_query_scoping_empty_when_no_tenant_assigned(db_session: Session):
    """Verify non-superadmin user with no assigned tenant receives zero records safely."""
    tenant_1 = uuid.uuid4()
    u1 = User(
        email="corp@t1.com",
        full_name="Corp User",
        hashed_password="hashed_pass_1",
        role=UserRole.VIEWER.value,
        tenant_id=tenant_1,
        is_active=True,
    )
    db_session.add(u1)
    db_session.commit()

    unassigned_user = AuthenticatedPrincipal(
        email="orphan@nowhere.com",
        tenant_id=None,
        role=UserRole.VIEWER.value,
        is_authenticated=True,
        is_super_admin=False,
    )

    base_query = db_session.query(User)
    scoped_query = TenantContext.scope_query(base_query, User, unassigned_user)
    results = scoped_query.all()

    assert len(results) == 0


def test_security_event_tenant_scoping(db_session: Session):
    """Verify security monitoring events respect tenant isolation boundaries."""
    t_a = uuid.uuid4()
    t_b = uuid.uuid4()

    # Pre-create tenants so foreign key matches
    db_session.add_all([
        Tenant(id=t_a, name="Tenant A", slug="tenant-a", is_active=True),
        Tenant(id=t_b, name="Tenant B", slug="tenant-b", is_active=True),
    ])
    db_session.commit()

    ev_a = SecurityEvent(
        id=uuid.uuid4(),
        tenant_id=t_a,
        event_type="LOGIN_SUCCESS",
        severity="INFORMATIONAL",
        user_email="alice@ta.com",
        details={},
    )
    ev_b = SecurityEvent(
        id=uuid.uuid4(),
        tenant_id=t_b,
        event_type="LOGIN_SUCCESS",
        severity="INFORMATIONAL",
        user_email="bob@tb.com",
        details={},
    )
    db_session.add_all([ev_a, ev_b])
    db_session.commit()

    principal_a = AuthenticatedPrincipal(
        email="auditor@ta.com",
        tenant_id=str(t_a),
        role=UserRole.SECURITY_AUDITOR.value,
        is_authenticated=True,
    )

    query = TenantContext.scope_query(db_session.query(SecurityEvent), SecurityEvent, principal_a)
    events = query.all()
    assert len(events) == 1
    assert events[0].user_email == "alice@ta.com"


def test_tenant_slug_uniqueness_enforced(db_session: Session):
    """Verify duplicate tenant slugs trigger database integrity violation."""
    from sqlalchemy.exc import IntegrityError

    t1 = Tenant(id=uuid.uuid4(), name="Company A", slug="unique-slug", is_active=True)
    t2 = Tenant(id=uuid.uuid4(), name="Company B", slug="unique-slug", is_active=True)
    db_session.add(t1)
    db_session.commit()

    db_session.add(t2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unauthenticated_principal_tenant_access_rejected():
    """Verify unauthenticated caller cannot claim tenant access."""
    anonymous = AuthenticatedPrincipal(
        email="anon@nowhere.com",
        tenant_id=str(uuid.uuid4()),
        role="VIEWER",
        is_authenticated=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        TenantContext.verify_tenant_access(anonymous, target_tenant_id=uuid.uuid4())
    assert exc_info.value.status_code == 403
