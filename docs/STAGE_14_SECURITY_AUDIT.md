# Stage 14: Comprehensive Enterprise Security, Identity & RBAC Architectural Audit

## Executive Summary

As part of **Stage 14: Role-Based Access Control (RBAC), Audit Logging & Enterprise Security Hardening** for CloudSage, this architectural security audit inspects the current repository state, reviews all authentication and authorization pathways from Stages 1–13, identifies critical security vulnerabilities and architectural gaps, and establishes the blueprint for production-grade security hardening.

---

## 1. Repository Provenance & Baseline Verification

- **Repository**: `https://github.com/ibharath-ofcl/CloudSage-Multi-Cloud-FinOps-Copilot-Background.git`
- **Base Branch**: `stage-13/advanced-anomaly-investigation`
- **Base Commit**: `313a959`
- **Stage 14 Feature Branch**: `stage-14/rbac-enterprise-security`
- **Working Tree Status**: Verified clean prior to branching.
- **Baseline Test Pass Count**: 439 tests passing (0 failures, 0 regressions across Stages 1–13).

---

## 2. Review of Existing Authentication & Authorization Implementations

### A. Stage 12 `AuthenticatedPrincipal` (`backend/app/alerts/security.py`)
In Stage 12, `get_authenticated_principal` was introduced to provide server-side principal resolution:
```python
def get_authenticated_principal(
    request: Request,
    db: Optional[Session] = None,
    authorization: Optional[str] = None,
    x_user_email: Optional[str] = None,
    x_user_role: Optional[str] = None,
) -> AuthenticatedPrincipal:
```

#### Vulnerabilities Identified:
1. **Unverified Header Trust**: If a client sends `X-User-Email: admin@enterprise.com` and `X-User-Role: SUPER_ADMIN`, the system honors these headers directly if Bearer token is absent, regardless of whether the request originates from a trusted internal reverse proxy or a hostile public client.
2. **Arbitrary Role Adoption**: If `candidate_email` is provided without an entry in the database, the function constructs an `AuthenticatedPrincipal` adopting whatever `candidate_role` was supplied in the request header (or defaulting to `FINOPS_ENGINEER`).
3. **Implicit Default Fallback**: If no authorization header or candidate email is provided, the function silently returns:
   ```python
   return AuthenticatedPrincipal(
       email="finops-lead@enterprise.com",
       role=UserRole.FINOPS_ENGINEER.value,
       full_name="Enterprise FinOps Lead",
       is_authenticated=True,
   )
   ```
   *Impact*: Any anonymous unauthenticated user calling endpoints relying on this fallback automatically gains full FinOps Engineer privileges!
4. **No Cryptographic JWT Verification**: Bearer tokens are evaluated using basic string prefix checks (`if "@" in token: candidate_email = token`) rather than verifying digital signatures (HMAC-SHA256 / RSA), claims (`exp`, `iss`, `aud`), or cryptographic authenticity.
5. **No Token Revocation or Session Invalidation**: The system has no mechanism to revoke an active token, invalidate a session upon logout, or disable access when an account is suspended.

### B. Stage 13 Investigation Routes (`backend/app/api/routes/investigations.py`)
Investigation endpoints wrap `get_authenticated_principal` in `get_current_principal`:
- Inherits the same fallback and header trust vulnerabilities.
- Lacks granular permission checks (relies only on broad `X-User-Role` checks).
- Lacks tenant or organizational scoping.

---

## 3. Review of Multi-Tenant Isolation & Account Scoping

### Findings:
1. **Absence of Tenant/Organization Model**:
   - `User` model contains `department`, but no `tenant_id` or `organization_id`.
   - Billing records, resources, anomalies, recommendations, and investigation cases store `account_id` (cloud provider account/subscription ID), but there is no overarching enterprise `tenant_id` partitioning different customer organizations.
2. **Risk of Insecure Direct Object Reference (IDOR)**:
   - An authenticated user in Organization A who knows the UUID of an anomaly or investigation case in Organization B can query or mutate that case if they possess an appropriate role.
3. **Dashboard & Copilot Cross-Tenant Leakage Risk**:
   - Dashboard aggregations filter by cloud provider and time window, but do not constrain queries to the caller's authorized tenant context.
   - The Copilot retrieval engine queries the global database without tenant boundary predicates.

---

## 4. Review of Data Models & Database Schema

### Existing Schema State (Alembic 001–011):
- `users`: Contains `id`, `email`, `full_name`, `hashed_password`, `role`, `department`, `is_active`, `created_at`.
  - *Missing*: `tenant_id`, `failed_login_attempts`, `locked_until`, `last_login_at`, password change timestamps.
- `audit_logs`: Contains `id`, `timestamp`, `user_id`, `user_email`, `action_type`, `resource_type`, `resource_id`, `before_state`, `after_state`, `client_ip`, `status`.
  - *Missing*: Cryptographic hash chaining (`previous_record_hash`, `record_hash`) to ensure tamper evidence.
  - *Missing*: Tenant context (`tenant_id`).
- *Missing Models*:
  - No `tenants` / `organizations` table.
  - No `roles` and `permissions` tables (currently role is a raw string column).
  - No `user_sessions` or `revoked_tokens` table for session revocation.
  - No `approval_requests` table for dual approval / separation of duties.
  - No `security_events` table for intrusion and threat detection.

---

## 5. Review of Secrets, Configuration & Deployment Settings

- `SECRET_KEY` in `backend/app/core/config.py` is hardcoded to a default development string.
- No environment validation checks whether `SECRET_KEY` has been changed in production mode.
- CORS origins default to `["http://localhost:3000", "http://localhost:5173"]`, which is appropriate for local dev, but needs explicit configuration validation for production.
- No reverse-proxy trust list (`TRUSTED_PROXY_IPS`) exists to validate `X-Forwarded-For` or `X-User-Email` headers.

---

## 6. Stage 14 Remediation Architecture & Target Blueprint

To eliminate all identified vulnerabilities, Stage 14 will implement:

1. **Centralized Security Package (`backend/app/security/`)**:
   - `token_service.py`: True cryptographic JWT issuance, signature verification, expiry enforcement, issuer/audience validation.
   - `password_service.py`: Secure Argon2id / bcrypt password hashing with salt and work factor.
   - `session_service.py`: Session tracking, active session limits, revocation lists, and refresh token rotation.
   - `principals.py`: Enhanced `AuthenticatedPrincipal` including `tenant_id`, `roles`, `permissions`, and `session_id`.
   - `permissions.py`: Granular `resource:action` permission taxonomy.
   - `roles.py`: 7-tier enterprise role mapping (`SUPER_ADMIN`, `ORGANIZATION_ADMIN`, `FINOPS_MANAGER`, `FINOPS_ANALYST`, `CLOUD_ENGINEER`, `SECURITY_AUDITOR`, `VIEWER`).
   - `authorization.py`: Reusable FastAPI dependencies (`require_permission`, `require_role`).
   - `tenant_context.py`: Thread-safe / context-managed tenant scoping enforcing query predicates and preventing IDOR.
   - `dual_approval.py`: Multi-party authorization workflows for sensitive administrative actions.
   - `audit_integrity.py`: Cryptographic SHA-256 hash chaining on audit logs for tamper evidence.
   - `threat_detection.py`: Security monitoring rules tracking brute force, privilege escalation, cross-tenant probing, and abnormal exports.

2. **Database Migration (`012_rbac_enterprise_security.py`)**:
   - Create `tenants`, `roles`, `permissions`, `role_permissions`, `user_roles`, `user_sessions`, `approval_requests`, `security_events`, `audit_checkpoints`.
   - Add `tenant_id` to `users`, `audit_logs`, and core domain tables.

3. **Production Startup Guardrails**:
   - Refuse startup in production if `SECRET_KEY` is default.
   - Reject unauthenticated development headers unless `ENVIRONMENT=development` AND `ALLOW_DEV_AUTH_HEADERS=true`.
   - Validate proxy IP before trusting forwarded headers.

4. **Frontend Security Admin Command Center**:
   - `/admin/users`: User provisioning, role assignment, deactivation, session revocation.
   - `/admin/roles`: Role list and granular permission matrix.
   - `/admin/security`: Threat detection dashboard, security events timeline, audit integrity validator, pending dual-approval requests.
   - `PermissionGate` and `RoleGate` components in React.
