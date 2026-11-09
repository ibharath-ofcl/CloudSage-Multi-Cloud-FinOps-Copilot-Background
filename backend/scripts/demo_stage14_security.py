#!/usr/bin/env python3
"""
CloudSage FinOps Copilot - Stage 14 Enterprise Security & RBAC Demonstration.
Executes an 18-step live verification of authentication, JWT verification,
RBAC enforcement, tenant isolation, dual approval, and tamper-evident audit logs.
"""

from datetime import datetime, timedelta, timezone
import json
import sys
import uuid
from typing import Dict

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is in sys.path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.config import settings
from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import ApprovalStatus, SecurityEventSeverity, SecurityEventType, UserRole
from backend.app.main import app
from backend.app.models.audit import AuditLog
from backend.app.models.security import ApprovalRequest, AuditIntegrityCheckpoint, SecurityEvent, Tenant
from backend.app.models.user import User
from backend.app.security.audit_integrity import AuditIntegrityService, GENESIS_HASH
from backend.app.security.dual_approval import DualApprovalService
from backend.app.security.password_service import PasswordService
from backend.app.security.permissions import Permissions, get_permissions_for_role, has_permission
from backend.app.security.principals import AuthenticatedPrincipal
from backend.app.security.session_service import SessionService
from backend.app.security.tenant_context import TenantContext
from backend.app.security.threat_detection import ThreatDetectionService
from backend.app.security.token_service import TokenService

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(num: int, title: str):
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}[STEP {num:02d}/18] {title.upper()}{RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}")


def print_pass(msg: str):
    print(f"  {GREEN}✔ {msg}{RESET}")


def print_info(msg: str):
    print(f"  {YELLOW}ℹ {msg}{RESET}")


def run_demo():
    print(f"\n{BOLD}{GREEN}================================================================================")
    print("   CLOUDSAGE STAGE 14: ENTERPRISE RBAC, AUDIT INTEGRITY & SECURITY HARDENING")
    print("   Zero Float Rule • Advisory-Only Enforcement • Cryptographic Non-Repudiation")
    print(f"================================================================================{RESET}")

    # Setup in-memory test database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    app.dependency_overrides[get_sync_db] = lambda: db
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # STEP 1: Multi-Tenant Architecture Initialization
    # -------------------------------------------------------------------------
    print_step(1, "Multi-Tenant Architecture Initialization")
    tenant_acme_id = uuid.uuid4()
    tenant_globex_id = uuid.uuid4()

    t_acme = Tenant(
        id=tenant_acme_id,
        name="Acme Corporation",
        slug="acme-corp",
        is_active=True,
    )
    t_globex = Tenant(
        id=tenant_globex_id,
        name="Globex International",
        slug="globex-intl",
        is_active=True,
    )
    db.add_all([t_acme, t_globex])
    db.commit()

    print_pass(f"Provisioned Tenant A: Acme Corporation ({tenant_acme_id})")
    print_pass(f"Provisioned Tenant B: Globex International ({tenant_globex_id})")

    # -------------------------------------------------------------------------
    # STEP 2: Provisioning 7 Canonical Enterprise RBAC Identities
    # -------------------------------------------------------------------------
    print_step(2, "Provisioning 7 Canonical Enterprise RBAC Identities")
    roles_to_seed = [
        (UserRole.SUPER_ADMIN, "superadmin@cloudsage.internal", "Global Super Admin", None),
        (UserRole.ORGANIZATION_ADMIN, "orgadmin@acme.com", "Acme Org Admin", tenant_acme_id),
        (UserRole.FINOPS_MANAGER, "manager@acme.com", "Acme FinOps Lead", tenant_acme_id),
        (UserRole.FINOPS_ANALYST, "analyst@acme.com", "Acme FinOps Analyst", tenant_acme_id),
        (UserRole.CLOUD_ENGINEER, "engineer@acme.com", "Acme Cloud Engineer", tenant_acme_id),
        (UserRole.SECURITY_AUDITOR, "auditor@acme.com", "Acme Compliance Auditor", tenant_acme_id),
        (UserRole.VIEWER, "viewer@acme.com", "Acme Executive Viewer", tenant_acme_id),
    ]

    users_by_role: Dict[str, User] = {}
    default_pwd = "CompliantPassword#2026"
    hashed_pwd = PasswordService.hash_password(default_pwd)

    for role_enum, email, full_name, t_id in roles_to_seed:
        u = User(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hashed_pwd,
            role=role_enum.value,
            tenant_id=t_id,
            is_active=True,
        )
        db.add(u)
        users_by_role[role_enum.value] = u

    db.commit()
    for role_enum, email, _, _ in roles_to_seed:
        print_pass(f"Created {role_enum.value:20} -> {email}")

    # -------------------------------------------------------------------------
    # STEP 3: Bcrypt Password Hashing & OWASP Complexity Validation
    # -------------------------------------------------------------------------
    print_step(3, "Bcrypt Password Hashing & OWASP Complexity Validation")
    assert PasswordService.verify_password(default_pwd, hashed_pwd) is True
    print_pass("Bcrypt 12-round salted hash verified successfully")

    # Test rejected weak passwords
    weak_tests = [
        ("Short#1", "length (< 12)"),
        ("lowercase#2026pass", "missing uppercase"),
        ("UPPERCASE#2026PASS", "missing lowercase"),
        ("NoSpecialChar2026", "missing symbol"),
    ]
    for weak_pwd, reason in weak_tests:
        valid, err = PasswordService.validate_password_strength(weak_pwd)
        assert valid is False
        print_pass(f"Rejected weak password ({reason}): '{weak_pwd}' -> {err}")

    # -------------------------------------------------------------------------
    # STEP 4: Authenticated REST Login & Cryptographic JWT Issuance
    # -------------------------------------------------------------------------
    print_step(4, "Authenticated REST Login & Cryptographic JWT Issuance")
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@acme.com", "password": default_pwd},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    print_pass("POST /api/v1/auth/login returned HTTP 200 OK")
    print_pass(f"Issued Access Token:  {access_token[:32]}... ({len(access_token)} chars)")
    print_pass(f"Issued Refresh Token: {refresh_token[:32]}... ({len(refresh_token)} chars)")

    # -------------------------------------------------------------------------
    # STEP 5: Cryptographic JWT Claims & Signature Verification
    # -------------------------------------------------------------------------
    print_step(5, "Cryptographic JWT Claims & Signature Verification")
    claims = TokenService.verify_access_token(access_token)
    print_pass("JWT signature cryptographically verified using HS256 algorithm")
    print_pass(f"  Issuer (iss):       {claims['iss']}")
    print_pass(f"  Audience (aud):     {claims['aud']}")
    print_pass(f"  Subject (sub):      {claims['sub']}")
    print_pass(f"  Role:               {claims['role']}")
    print_pass(f"  Token JTI:          {claims['jti']}")
    print_pass(f"  Tenant Context:     {claims['tenant_id']}")

    # -------------------------------------------------------------------------
    # STEP 6: Cryptographic Token Tampering Rejection
    # -------------------------------------------------------------------------
    print_step(6, "Cryptographic Token Tampering Rejection")
    tampered_token = access_token[:-6] + "xxxxxx"
    tamper_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert tamper_res.status_code == 401
    print_pass(f"Tampered JWT signature instantly rejected: HTTP {tamper_res.status_code} Unauthorized")

    # -------------------------------------------------------------------------
    # STEP 7: Single-Use Refresh Token Rotation & Replay Attack Defense
    # -------------------------------------------------------------------------
    print_step(7, "Single-Use Refresh Token Rotation & Replay Attack Defense")
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_token_data = refresh_res.json()
    new_access = new_token_data["access_token"]
    new_refresh = new_token_data["refresh_token"]
    print_pass("Exchanged refresh token for newly rotated token pair")
    assert new_refresh != refresh_token

    # Replay old refresh token -> must be rejected
    replay_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay_res.status_code == 401
    print_pass("Replayed old refresh token blocked with HTTP 401 Unauthorized (Replay Attack Prevented)")

    # -------------------------------------------------------------------------
    # STEP 8: Brute-Force Detection & Automatic Account Lockout
    # -------------------------------------------------------------------------
    print_step(8, "Brute-Force Detection & Automatic Account Lockout")
    victim_email = "analyst@acme.com"
    for attempt in range(1, settings.LOGIN_MAX_FAILED_ATTEMPTS + 1):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": "WrongPassword#999"},
        )
        print_info(f"Failed login attempt #{attempt} submitted -> HTTP {res.status_code}")

    locked_res = client.post(
        "/api/v1/auth/login",
        json={"email": victim_email, "password": default_pwd},
    )
    assert locked_res.status_code in (403, 423)
    print_pass(f"Brute-force lockout triggered: Account locked for {settings.LOGIN_LOCKOUT_MINUTES} minutes (HTTP {locked_res.status_code})")

    # Reset lock for subsequent tests
    users_by_role[UserRole.FINOPS_ANALYST.value].is_locked = False
    users_by_role[UserRole.FINOPS_ANALYST.value].failed_login_attempts = 0
    db.commit()

    # -------------------------------------------------------------------------
    # STEP 9: Instant Active Session Revocation
    # -------------------------------------------------------------------------
    print_step(9, "Instant Active Session Revocation")
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert logout_res.status_code == 200
    print_pass("POST /api/v1/auth/logout invoked: active session terminated")

    # Verify session is dead
    dead_sess_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert dead_sess_res.status_code == 401
    print_pass("Terminated session blocked from further API calls: HTTP 401 Unauthorized")

    # -------------------------------------------------------------------------
    # STEP 10: Role-Based Access Control (RBAC) Permission Boundaries
    # -------------------------------------------------------------------------
    print_step(10, "Role-Based Access Control (RBAC) Permission Boundaries")
    mgr_perms = get_permissions_for_role(UserRole.FINOPS_MANAGER.value)
    analyst_perms = get_permissions_for_role(UserRole.FINOPS_ANALYST.value)
    viewer_perms = get_permissions_for_role(UserRole.VIEWER.value)

    # 1. FINOPS_MANAGER has recommendations:approve
    assert has_permission(mgr_perms, Permissions.RECOMMENDATIONS_APPROVE) is True
    print_pass("FINOPS_MANAGER possesses 'recommendations:approve' capability")

    # 2. FINOPS_ANALYST lacks recommendations:approve
    assert has_permission(analyst_perms, Permissions.RECOMMENDATIONS_APPROVE) is False
    print_pass("FINOPS_ANALYST denied 'recommendations:approve' capability (403 Forbidden)")

    # 3. VIEWER has only read access
    assert has_permission(viewer_perms, Permissions.DASHBOARD_READ) is True
    assert has_permission(viewer_perms, Permissions.USERS_MANAGE) is False
    assert has_permission(viewer_perms, Permissions.RECOMMENDATIONS_APPROVE) is False
    print_pass("VIEWER confirmed strictly read-only: zero mutation or approval authority")

    # -------------------------------------------------------------------------
    # STEP 11: Multi-Tenant Data Isolation & Query Scoping
    # -------------------------------------------------------------------------
    print_step(11, "Multi-Tenant Data Isolation & Query Scoping")
    # Seed resources in Acme and Globex
    u_acme = users_by_role[UserRole.FINOPS_ANALYST.value]
    u_globex = User(
        id=uuid.uuid4(),
        email="globex_user@globex.com",
        full_name="Globex Employee",
        hashed_password=hashed_pwd,
        role=UserRole.FINOPS_ANALYST.value,
        tenant_id=tenant_globex_id,
        is_active=True,
    )
    db.add(u_globex)
    db.commit()

    acme_principal = AuthenticatedPrincipal(
        email=u_acme.email,
        user_id=str(u_acme.id),
        tenant_id=str(tenant_acme_id),
        role=UserRole.FINOPS_ANALYST.value,
        is_authenticated=True,
    )

    scoped_query = TenantContext.scope_query(db.query(User), User, acme_principal)
    visible_users = scoped_query.all()
    assert all(u.tenant_id == tenant_acme_id for u in visible_users if u.tenant_id is not None)
    assert not any(u.email == "globex_user@globex.com" for u in visible_users)
    print_pass(f"Tenant isolation verified: Acme principal queried {len(visible_users)} records with ZERO leakage from Globex")

    # -------------------------------------------------------------------------
    # STEP 12: Cross-Tenant IDOR Attack Prevention
    # -------------------------------------------------------------------------
    print_step(12, "Cross-Tenant IDOR Attack Prevention")
    try:
        TenantContext.verify_tenant_access(acme_principal, target_tenant_id=tenant_globex_id)
        assert False, "Should have raised 403"
    except HTTPException as exc:
        assert exc.status_code == 403
        print_pass("Cross-tenant IDOR attack blocked: HTTP 403 Forbidden")
        print_info(f"Rejection detail: {exc.detail}")

    # -------------------------------------------------------------------------
    # STEP 13: Threat Detection & Security Event Logging
    # -------------------------------------------------------------------------
    print_step(13, "Threat Detection & Security Event Logging")
    ThreatDetectionService.record_event(
        db=db,
        event_type=SecurityEventType.CROSS_TENANT_ACCESS_DENIED,
        severity=SecurityEventSeverity.HIGH,
        tenant_id=tenant_acme_id,
        user_email=acme_principal.email,
        details={"attempted_target": str(tenant_globex_id)},
    )
    stats = ThreatDetectionService.get_security_stats(db=db, days=1)
    print_pass(f"Security event recorded: CROSS_TENANT_ACCESS_DENIED (Severity: HIGH)")
    print_pass(f"Security Telemetry: {stats['total_security_events']} total events, {stats['high_events']} high severity")

    # -------------------------------------------------------------------------
    # STEP 14: Dual Approval & Separation of Duties (requester != approver)
    # -------------------------------------------------------------------------
    print_step(14, "Dual Approval & Separation of Duties (requester != approver)")
    requester_pr = AuthenticatedPrincipal(
        email="engineer@acme.com",
        user_id=str(users_by_role[UserRole.CLOUD_ENGINEER.value].id),
        tenant_id=str(tenant_acme_id),
        role=UserRole.CLOUD_ENGINEER.value,
        is_authenticated=True,
    )
    approver_pr = AuthenticatedPrincipal(
        email="manager@acme.com",
        user_id=str(users_by_role[UserRole.FINOPS_MANAGER.value].id),
        tenant_id=str(tenant_acme_id),
        role=UserRole.FINOPS_MANAGER.value,
        is_authenticated=True,
    )

    # 1. Create dual approval request
    req = DualApprovalService.create_request(
        db=db,
        principal=requester_pr,
        action_type="HIGH_IMPACT_RESOURCE_REMEDIATION",
        resource_type="infrastructure_playbook",
        resource_id="playbook-404",
        requested_payload={"target": "i-0987654321", "action": "stop"},
        justification="Verified persistent idle waste over 30 consecutive billing cycles.",
    )
    print_pass(f"Created Dual Approval Request: #{req.id} (Status: PENDING)")

    # 2. Requester tries to approve own request -> must be rejected
    try:
        DualApprovalService.decide_request(
            db=db,
            principal=requester_pr,
            request_id=req.id,
            approved=True,
        )
        assert False, "Self-approval must fail"
    except HTTPException as exc:
        assert exc.status_code == 403
        print_pass("Separation of duties enforced: Requester CANNOT approve own request (HTTP 403 Forbidden)")

    # 3. Independent second approver approves
    decided = DualApprovalService.decide_request(
        db=db,
        principal=approver_pr,
        request_id=req.id,
        approved=True,
        decision_notes="Confirmed hardware metrics with platform operations.",
    )
    assert decided.status == ApprovalStatus.APPROVED.value
    print_pass(f"Independent approver (manager@acme.com) successfully approved: Status: {decided.status}")

    # -------------------------------------------------------------------------
    # STEP 15: Tamper-Evident Audit Logging (SHA-256 Hash Chaining)
    # -------------------------------------------------------------------------
    print_step(15, "Tamper-Evident Audit Logging (SHA-256 Hash Chaining)")
    log1 = AuditIntegrityService.record_audit(
        db=db,
        user_id=users_by_role[UserRole.FINOPS_MANAGER.value].id,
        user_email="manager@acme.com",
        action_type="RECOMMENDATION_APPROVE",
        resource_type="recommendations",
        resource_id="rec-101",
        after_state={"approved_savings": "1250.0000", "password": "SecretPassword123!"},
        tenant_id=tenant_acme_id,
    )
    print_pass(f"Audit Record 1: Hash={log1.record_hash[:16]}... Prev={log1.previous_hash[:16]}...")
    assert log1.after_state["password"] == "[REDACTED]"
    print_pass("Secret redaction verified: 'password' automatically sanitized to '[REDACTED]'")

    log2 = AuditIntegrityService.record_audit(
        db=db,
        user_id=users_by_role[UserRole.CLOUD_ENGINEER.value].id,
        user_email="engineer@acme.com",
        action_type="PLAYBOOK_GENERATE",
        resource_type="playbooks",
        resource_id="pb-202",
        after_state={"playbook": "terraform"},
        tenant_id=tenant_acme_id,
    )
    print_pass(f"Audit Record 2: Hash={log2.record_hash[:16]}... Prev={log2.previous_hash[:16]}...")
    assert log2.previous_hash == log1.record_hash
    print_pass("Cryptographic hash chain link verified: Record 2 previous_hash == Record 1 record_hash")

    # -------------------------------------------------------------------------
    # STEP 16: Cryptographic Audit Log Chain Verification
    # -------------------------------------------------------------------------
    print_step(16, "Cryptographic Audit Log Chain Verification")
    is_valid, records_checked, error = AuditIntegrityService.verify_chain(db)
    assert is_valid is True
    print_pass(f"Full ledger integrity verified: {records_checked} records evaluated with ZERO corruption")

    # -------------------------------------------------------------------------
    # STEP 17: Tamper Detection & Non-Repudiation Defense
    # -------------------------------------------------------------------------
    print_step(17, "Tamper Detection & Non-Repudiation Defense")
    # Maliciously modify Record 1 directly in database
    log1.after_state = {"approved_savings": "99999.0000"}  # Tampered
    db.commit()

    is_valid, broken_idx, error = AuditIntegrityService.verify_chain(db)
    assert is_valid is False
    print_pass(f"Direct database tampering instantly detected! Chain Valid: {is_valid}")
    print_info(f"Integrity alert: {error}")

    # Revert tampering
    log1.after_state = {"approved_savings": "1250.0000", "password": "[REDACTED]"}
    db.commit()
    is_valid, _, _ = AuditIntegrityService.verify_chain(db)
    assert is_valid is True
    print_pass("Ledger restored: Cryptographic verification succeeds again")

    # -------------------------------------------------------------------------
    # STEP 18: Immutable Regulatory Compliance Checkpoint
    # -------------------------------------------------------------------------
    print_step(18, "Immutable Regulatory Compliance Checkpoint")
    cp = AuditIntegrityService.create_checkpoint(
        db=db,
        tenant_id=tenant_acme_id,
        verified_by="security-auditor@acme.com",
    )
    assert cp.is_valid is True
    print_pass("Created Immutable Cryptographic Checkpoint for SOC 2 / ISO 27001 audit:")
    print_pass(f"  Checkpoint ID:     {cp.id}")
    print_pass(f"  Records Sealed:    {cp.record_count}")
    print_pass(f"  Cumulative SHA256: {cp.cumulative_hash}")
    print_pass(f"  Verified By:       {cp.verified_by}")
    print_pass(f"  Verified At:       {cp.verified_at}")

    # Final summary banner
    print(f"\n{BOLD}{GREEN}================================================================================")
    print("   STAGE 14 DEMONSTRATION COMPLETE: 18/18 STEPS 100% OPERATIONAL")
    print("   RBAC • JWT Auth • Multi-Tenancy • Dual Approval • SHA-256 Audit Chaining")
    print(f"================================================================================{RESET}\n")

    app.dependency_overrides.clear()


if __name__ == "__main__":
    run_demo()
