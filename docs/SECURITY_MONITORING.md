# CloudSage Security Monitoring & Threat Detection

## 1. Overview
CloudSage features an integrated real-time threat detection and security event telemetry engine (`ThreatDetectionService`). It proactively detects, logs, alerts on, and mitigates unauthorized behavior across identity, session, and tenant boundaries.

---

## 2. Threat Event Taxonomy

| Event Type | Default Severity | Trigger Condition | Automated Mitigation |
| :--- | :--- | :--- | :--- |
| `LOGIN_SUCCESS` | `INFORMATIONAL` | Valid credentials submitted via `/api/v1/auth/login`. | Resets failed login attempt counter to 0, updates `last_login_at`. |
| `LOGIN_FAILURE` | `MEDIUM` | Incorrect password or unmapped email. | Increments user `failed_login_attempts`. |
| `ACCOUNT_LOCKED` | `CRITICAL` | Exceeded 5 failed login attempts in 15 minutes. | Sets `is_locked=True`, blocks logins with HTTP 423 for 15 minutes. |
| `ACCOUNT_UNLOCKED` | `MEDIUM` | Admin manual unlock or expiration of lockout timer. | Resets lockout flags, allows authentication. |
| `TOKEN_REFRESH` | `INFORMATIONAL` | Legitimate single-use refresh token exchange. | Issues new token pair, rotates refresh hash. |
| `TOKEN_REVOCATION` | `INFORMATIONAL` | User logout or administrator session revocation. | Marks session record `REVOKED`. |
| `AUTH_FAILURE` | `MEDIUM` | Principal lacks required permission or role for an endpoint. | Rejects with HTTP 403 Forbidden. |
| `CROSS_TENANT_ACCESS_DENIED` | `HIGH` | Principal attempts IDOR access to another tenant's entity. | Rejects with HTTP 403 Forbidden, alerts security dashboard. |
| `PRIVILEGE_ESCALATION_ATTEMPT` | `HIGH` | Non-superadmin attempts to provision or grant `SUPER_ADMIN`. | Rejects with HTTP 403 Forbidden. |
| `APPROVAL_REQUESTED` | `INFORMATIONAL` | User submits high-risk action for dual approval. | Transitions request to PENDING. |
| `APPROVAL_GRANTED` | `INFORMATIONAL` | Independent second approver grants request. | Records decision notes and approver ID. |
| `APPROVAL_REJECTED` | `MEDIUM` | Second approver rejects request. | Records rejection rationale. |

---

## 3. Security Telemetry Dashboard & Metrics

The `/api/v1/admin/security/stats` endpoint and `/admin/security` frontend page surface vital security posture indicators:
- **Active Sessions**: Total concurrently active JWT sessions across the platform.
- **Locked Accounts**: Current count of user accounts under brute-force lockout.
- **Pending Dual Approvals**: High-risk actions awaiting independent second-party review.
- **Threat Events (24h)**: Aggregated count of security events in the last 24 hours.
- **Critical Severity Events**: Priority alerts requiring immediate triage.
- **Audit Chain Integrity State**: Live Boolean indicator reflecting whether the SHA-256 hash chain is unbroken.

---

## 4. Threat Response & Incident Handling Workflow

```
[ Security Event Detected ]
         │
         ├── CRITICAL (Lockout) ──────> Automated 15-Minute Temporary Lockout
         │
         ├── HIGH (Cross-Tenant/Escalation) -> Log Security Event & Alert Dashboard
         │
         └── MEDIUM (Auth Failure) ───> Log Telemetry & Return 403
```
