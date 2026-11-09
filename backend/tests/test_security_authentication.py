"""
Stage 14 Test Suite: Cryptographic Authentication, JWT Verification & Session Lifecycle.
Verifies bcrypt 12-round password hashing, OWASP strength rules, JWT validation,
single-use refresh token rotation, lockout protection, and session revocation.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.database import get_sync_db
from backend.app.core.enums import UserRole
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.security import UserSession
from backend.app.security.password_service import PasswordService
from backend.app.security.token_service import TokenService
from backend.app.security.session_service import SessionService


def test_password_hashing_and_verification():
    """Verify bcrypt hashes passwords securely and matches correctly."""
    plain = "SuperSecureFinOps#2026"
    hashed = PasswordService.hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert PasswordService.verify_password(plain, hashed) is True
    assert PasswordService.verify_password("WrongPassword123!", hashed) is False


def test_password_complexity_rules():
    """Verify OWASP-aligned complexity rules require length, casing, numbers, and symbols."""
    # Valid password
    valid, err = PasswordService.validate_password_strength("CloudSage#2026Pass")
    assert valid is True
    assert err is None

    # Too short (< 12)
    valid, err = PasswordService.validate_password_strength("Short#1")
    assert valid is False
    assert f"at least {settings.PASSWORD_MIN_LENGTH}" in err

    # Missing uppercase
    valid, err = PasswordService.validate_password_strength("lowercase#2026pass")
    assert valid is False
    assert "uppercase" in err

    # Missing lowercase
    valid, err = PasswordService.validate_password_strength("UPPERCASE#2026PASS")
    assert valid is False
    assert "lowercase" in err

    # Missing digit
    valid, err = PasswordService.validate_password_strength("NoDigitsSpecial#")
    assert valid is False
    assert "digit" in err

    # Missing special character
    valid, err = PasswordService.validate_password_strength("NoSpecialChar2026")
    assert valid is False
    assert "special" in err


def test_jwt_issuance_and_claims():
    """Verify JWT access token embeds all mandatory RFC 7519 and CloudSage claims."""
    user_id = "test-user-uuid-123"
    email = "lead@enterprise.com"
    role = UserRole.FINOPS_MANAGER.value

    token = TokenService.create_access_token(
        user_id=user_id,
        email=email,
        role=role,
    )
    assert isinstance(token, str)

    payload = TokenService.verify_access_token(token)
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["role"] == role
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert "jti" in payload
    assert "exp" in payload


def test_jwt_tampering_rejection():
    """Verify that tampering with token characters or signature raises 401."""
    token = TokenService.create_access_token(
        user_id="user-1",
        email="test@enterprise.com",
        role=UserRole.VIEWER.value,
    )
    tampered = token[:-4] + "abcd"

    with pytest.raises(HTTPException) as exc_info:
        TokenService.verify_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_jwt_expiration_rejection():
    """Verify expired JWT tokens are rejected with 401."""
    token = TokenService.create_access_token(
        user_id="user-expired",
        email="expired@enterprise.com",
        role=UserRole.VIEWER.value,
        expires_delta=timedelta(seconds=-10),  # Already expired
    )

    with pytest.raises(HTTPException) as exc_info:
        TokenService.verify_access_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_session_lifecycle_and_single_use_refresh_rotation(db_session):
    """Verify user session creation, active status, single-use refresh rotation, and revocation."""
    # Seed user
    user = User(
        email="session-test@enterprise.com",
        hashed_password=PasswordService.hash_password("ValidPassword#123"),
        full_name="Session Tester",
        role=UserRole.FINOPS_ANALYST.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # 1. Create session
    session, access_token, refresh_token = SessionService.create_session(
        db=db_session,
        user=user,
        client_ip="127.0.0.1",
        user_agent="PyTest-Agent/1.0",
    )
    assert session.status == "ACTIVE"
    assert session.user_id == user.id

    # 2. Rotate refresh token
    new_access, new_refresh = SessionService.refresh_session(
        db=db_session,
        refresh_token=refresh_token,
        client_ip="127.0.0.1",
    )
    assert new_access != access_token
    assert new_refresh != refresh_token

    # 3. Old refresh token reuse should be rejected (replay attack detection)
    with pytest.raises(HTTPException) as exc_info:
        SessionService.refresh_session(
            db=db_session,
            refresh_token=refresh_token,  # Reusing old token
        )
    assert exc_info.value.status_code == 401

    # 4. Revoke session
    revoked = SessionService.revoke_session(db=db_session, session_id=session.id)
    assert revoked is True
    refreshed_session = db_session.query(UserSession).filter(UserSession.id == session.id).first()
    assert refreshed_session.status == "REVOKED"


def test_auth_login_api_flow(db_session):
    """Test /api/v1/auth/login endpoint with valid and invalid credentials."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(app)

    password = "ValidPassword#2026"
    user = User(
        email="auth-api@enterprise.com",
        hashed_password=PasswordService.hash_password(password),
        full_name="Auth API User",
        role=UserRole.FINOPS_MANAGER.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Successful login
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "auth-api@enterprise.com", "password": password},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "auth-api@enterprise.com"
    assert data["user"]["role"] == UserRole.FINOPS_MANAGER.value

    # Failed login: bad password
    bad_res = client.post(
        "/api/v1/auth/login",
        json={"email": "auth-api@enterprise.com", "password": "WrongPassword#999"},
    )
    assert bad_res.status_code == 401

    app.dependency_overrides.clear()


def test_auth_account_lockout_on_brute_force(db_session):
    """Verify repeated failed login attempts lock account with HTTP 423."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(app)

    user = User(
        email="lockout-target@enterprise.com",
        hashed_password=PasswordService.hash_password("ValidPassword#2026"),
        full_name="Lockout Target",
        role=UserRole.VIEWER.value,
        is_active=True,
        failed_login_attempts=4,  # 1 short of 5 max attempts
    )
    db_session.add(user)
    db_session.commit()

    # 5th failed attempt -> locks account
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "lockout-target@enterprise.com", "password": "BadPassword#1"},
    )
    assert res.status_code in (401, 423)

    # 6th attempt should be rejected with 423 Locked
    locked_res = client.post(
        "/api/v1/auth/login",
        json={"email": "lockout-target@enterprise.com", "password": "ValidPassword#2026"},
    )
    assert locked_res.status_code == 423
    assert "locked" in locked_res.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_auth_refresh_and_logout_endpoints(db_session):
    """Test /api/v1/auth/refresh and /api/v1/auth/logout endpoints."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(app)

    password = "ValidPassword#2026"
    user = User(
        email="refresh-user@enterprise.com",
        hashed_password=PasswordService.hash_password(password),
        full_name="Refresh User",
        role=UserRole.FINOPS_ANALYST.value,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh-user@enterprise.com", "password": password},
    )
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]
    access_token = tokens["access_token"]

    # Refresh
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert new_tokens["access_token"] != access_token

    # Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"

    app.dependency_overrides.clear()


def test_auth_me_endpoint_returns_current_principal(db_session):
    """Test /api/v1/auth/me returns current user identity with mapped permissions."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(app)

    password = "ValidPassword#2026"
    user = User(
        email="me-user@enterprise.com",
        hashed_password=PasswordService.hash_password(password),
        full_name="Me User",
        role=UserRole.FINOPS_MANAGER.value,
        department="FinOps Leadership",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "me-user@enterprise.com", "password": password},
    )
    access_token = login_res.json()["access_token"]

    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "me-user@enterprise.com"
    assert data["role"] == UserRole.FINOPS_MANAGER.value
    assert data["department"] == "FinOps Leadership"
    assert "recommendations:approve" in data["permissions"]

    app.dependency_overrides.clear()


def test_unauthenticated_request_rejected_without_token(db_session):
    """Verify endpoints requiring authentication return 401 Unauthorized when no credentials provided."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(app)

    # In production without dev headers, anonymous call to /api/v1/auth/me must fail with 401
    orig_env = settings.ENVIRONMENT
    orig_dev = settings.ALLOW_DEV_AUTH_HEADERS
    try:
        settings.ENVIRONMENT = "production"
        settings.ALLOW_DEV_AUTH_HEADERS = False

        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401
    finally:
        settings.ENVIRONMENT = orig_env
        settings.ALLOW_DEV_AUTH_HEADERS = orig_dev
        app.dependency_overrides.clear()


def test_deactivated_user_login_prevented(db_session):
    """Verify deactivated accounts cannot log in even with correct password."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    client = TestClient(app)

    password = "ValidPassword#2026"
    user = User(
        email="deactivated@enterprise.com",
        hashed_password=PasswordService.hash_password(password),
        full_name="Deactivated User",
        role=UserRole.VIEWER.value,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "deactivated@enterprise.com", "password": password},
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()

    app.dependency_overrides.clear()
