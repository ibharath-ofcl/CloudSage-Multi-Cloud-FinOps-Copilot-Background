"""
Stage 14 Test Suite: Dual-Party Governance & Separation of Duties.
Validates multi-party approval workflows, requester != approver invariant,
expiration enforcement, and tenant scoping.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.core.enums import ApprovalStatus, UserRole
from backend.app.models.security import ApprovalRequest, Tenant
from backend.app.security.dual_approval import DualApprovalService
from backend.app.security.principals import AuthenticatedPrincipal


def test_create_approval_request_success(db_session: Session):
    """Verify creating a valid dual approval request persists with PENDING status."""
    requester = AuthenticatedPrincipal(
        email="eng-lead@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.CLOUD_ENGINEER.value,
        is_authenticated=True,
    )

    req = DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="UPDATE_SECURITY_POLICY",
        resource_type="tenant_policies",
        resource_id="policy-1",
        requested_payload={"mfa_enforced": True},
        justification="Enforcing corporate MFA compliance for SOC 2 certification.",
    )

    assert req.id is not None
    assert req.status == ApprovalStatus.PENDING.value
    assert req.requester_email == "eng-lead@enterprise.com"
    assert req.action_type == "UPDATE_SECURITY_POLICY"


def test_create_approval_request_requires_justification(db_session: Session):
    """Verify requests with short or empty justification are rejected with 400 Bad Request."""
    requester = AuthenticatedPrincipal(
        email="eng-lead@enterprise.com",
        role=UserRole.CLOUD_ENGINEER.value,
        is_authenticated=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        DualApprovalService.create_request(
            db=db_session,
            principal=requester,
            action_type="TEST_ACTION",
            resource_type="res",
            resource_id="1",
            requested_payload={},
            justification="Too short",  # < 10 characters
        )
    assert exc_info.value.status_code == 400
    assert "justification" in exc_info.value.detail.lower()


def test_separation_of_duties_requester_cannot_approve_own_request(db_session: Session):
    """Verify requester is blocked from approving their own request (requester != approver)."""
    user_id = str(uuid.uuid4())
    requester = AuthenticatedPrincipal(
        email="admin@enterprise.com",
        user_id=user_id,
        role=UserRole.ORGANIZATION_ADMIN.value,
        is_authenticated=True,
    )

    req = DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="GRANT_SUPER_ADMIN",
        resource_type="users",
        resource_id="user-2",
        requested_payload={"role": "SUPER_ADMIN"},
        justification="Assigning emergency break-glass authority to user.",
    )

    # Requester tries to approve their own request -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        DualApprovalService.decide_request(
            db=db_session,
            principal=requester,
            request_id=req.id,
            approved=True,
            decision_notes="Self-approving my own request",
        )
    assert exc_info.value.status_code == 403
    assert "separation of duties" in exc_info.value.detail.lower()


def test_independent_second_party_approval_success(db_session: Session):
    """Verify an independent second authorized principal can successfully approve a request."""
    requester = AuthenticatedPrincipal(
        email="requester@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )
    approver = AuthenticatedPrincipal(
        email="manager@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )

    req = DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="DISMISS_MAJOR_ANOMALY",
        resource_type="anomalies",
        resource_id="anom-999",
        requested_payload={"status": "DISMISSED"},
        justification="Verified legitimate load testing batch in staging environment.",
    )

    decided = DualApprovalService.decide_request(
        db=db_session,
        principal=approver,
        request_id=req.id,
        approved=True,
        decision_notes="Confirmed load test schedule with DevOps team.",
    )

    assert decided.status == ApprovalStatus.APPROVED.value
    assert decided.approver_email == "manager@enterprise.com"
    assert decided.decision_notes == "Confirmed load test schedule with DevOps team."
    assert decided.decided_at is not None


def test_independent_second_party_rejection(db_session: Session):
    """Verify an independent second party can reject a request with audit notes."""
    requester = AuthenticatedPrincipal(
        email="requester@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )
    approver = AuthenticatedPrincipal(
        email="auditor@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.SECURITY_AUDITOR.value,
        is_authenticated=True,
    )

    req = DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="BYPASS_POLICY",
        resource_type="tenant",
        resource_id="1",
        requested_payload={},
        justification="Requesting temporary exception to cost center tagging rules.",
    )

    rejected = DualApprovalService.decide_request(
        db=db_session,
        principal=approver,
        request_id=req.id,
        approved=False,
        decision_notes="Policy exceptions require VP sign-off per corporate governance handbook.",
    )

    assert rejected.status == ApprovalStatus.REJECTED.value
    assert rejected.approver_email == "auditor@enterprise.com"


def test_re_deciding_already_decided_request_rejected(db_session: Session):
    """Verify attempting to decide an already approved or rejected request raises 400 Bad Request."""
    requester = AuthenticatedPrincipal(
        email="req@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )
    approver1 = AuthenticatedPrincipal(
        email="mgr1@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )
    approver2 = AuthenticatedPrincipal(
        email="mgr2@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )

    req = DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="RULE_MUTATION",
        resource_type="rules",
        resource_id="rule-1",
        requested_payload={},
        justification="Valid justification for changing alerting threshold.",
    )

    # First decision succeeds
    DualApprovalService.decide_request(
        db=db_session,
        principal=approver1,
        request_id=req.id,
        approved=True,
    )

    # Second decision fails with 400
    with pytest.raises(HTTPException) as exc_info:
        DualApprovalService.decide_request(
            db=db_session,
            principal=approver2,
            request_id=req.id,
            approved=False,
        )
    assert exc_info.value.status_code == 400
    assert "already in state" in exc_info.value.detail.lower()


def test_expired_approval_request_cannot_be_decided(db_session: Session):
    """Verify expired requests cannot be approved and transition to EXPIRED."""
    requester = AuthenticatedPrincipal(
        email="req@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.CLOUD_ENGINEER.value,
        is_authenticated=True,
    )
    approver = AuthenticatedPrincipal(
        email="mgr@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )

    # Create expired request directly in database
    past = datetime.now(timezone.utc) - timedelta(hours=48)
    expired_req = ApprovalRequest(
        id=uuid.uuid4(),
        requester_id=UUID(requester.user_id),
        requester_email=requester.email,
        action_type="EXPIRED_ACTION",
        resource_type="res",
        resource_id="1",
        requested_payload={},
        justification="Old justification that is now expired.",
        status=ApprovalStatus.PENDING.value,
        created_at=past,
        expires_at=past + timedelta(hours=24),
    )
    db_session.add(expired_req)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        DualApprovalService.decide_request(
            db=db_session,
            principal=approver,
            request_id=expired_req.id,
            approved=True,
        )
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()


def test_cross_tenant_approval_decision_denied(db_session: Session):
    """Verify approver from Tenant A cannot decide request from Tenant B."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Pre-create tenants for FK
    db_session.add_all([
        Tenant(id=tenant_a, name="Tenant Alpha", slug="alpha-tenant", is_active=True),
        Tenant(id=tenant_b, name="Tenant Beta", slug="beta-tenant", is_active=True),
    ])
    db_session.commit()

    requester_a = AuthenticatedPrincipal(
        email="user@alpha.com",
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_a),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )
    approver_b = AuthenticatedPrincipal(
        email="mgr@beta.com",
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_b),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )

    req = DualApprovalService.create_request(
        db=db_session,
        principal=requester_a,
        action_type="TENANT_ACTION",
        resource_type="reports",
        resource_id="rep-1",
        requested_payload={},
        justification="Legitimate justification within tenant Alpha.",
    )

    with pytest.raises(HTTPException) as exc_info:
        DualApprovalService.decide_request(
            db=db_session,
            principal=approver_b,
            request_id=req.id,
            approved=True,
        )
    assert exc_info.value.status_code == 403
    assert "cross-tenant" in exc_info.value.detail.lower()


def test_list_requests_by_status(db_session: Session):
    """Verify list_requests filters by PENDING and APPROVED states."""
    requester = AuthenticatedPrincipal(
        email="lister@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.CLOUD_ENGINEER.value,
        is_authenticated=True,
    )
    approver = AuthenticatedPrincipal(
        email="decider@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )

    # 1st request: PENDING
    DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="ACTION_1",
        resource_type="res",
        resource_id="1",
        requested_payload={},
        justification="Valid justification for action number one.",
    )

    # 2nd request: APPROVED
    r2 = DualApprovalService.create_request(
        db=db_session,
        principal=requester,
        action_type="ACTION_2",
        resource_type="res",
        resource_id="2",
        requested_payload={},
        justification="Valid justification for action number two.",
    )
    DualApprovalService.decide_request(
        db=db_session,
        principal=approver,
        request_id=r2.id,
        approved=True,
    )

    pending_list = DualApprovalService.list_requests(db_session, status_filter="PENDING")
    assert len(pending_list) == 1
    assert pending_list[0].action_type == "ACTION_1"

    approved_list = DualApprovalService.list_requests(db_session, status_filter="APPROVED")
    assert len(approved_list) == 1
    assert approved_list[0].action_type == "ACTION_2"


def test_decide_non_existent_request_raises_404(db_session: Session):
    """Verify deciding a non-existent approval request raises 404 Not Found."""
    approver = AuthenticatedPrincipal(
        email="auditor@enterprise.com",
        user_id=str(uuid.uuid4()),
        role=UserRole.SECURITY_AUDITOR.value,
        is_authenticated=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        DualApprovalService.decide_request(
            db=db_session,
            principal=approver,
            request_id=uuid.uuid4(),
            approved=True,
        )
    assert exc_info.value.status_code == 404
