# CloudSage Authentication & Credential Security

## 1. Overview
CloudSage implements a centralized, zero-trust authentication architecture designed to eliminate vulnerabilities identified in early stages (such as trusting client-supplied identity headers). Every request is verified cryptographically.

---

## 2. Password Security & Bcrypt Storage

### Hashing Algorithm
- **Algorithm**: `bcrypt` (Blowfish-based adaptive hashing).
- **Work Factor (Cost)**: `12 rounds` (computationally hardened against GPU/ASIC rainbow table attacks).
- **Salt Generation**: Automatically generated cryptographically random salt per user.

### OWASP Password Strength Requirements
Every password submitted during registration or user provisioning must satisfy:
1. Minimum length: **12 characters** (configurable via `PASSWORD_MIN_LENGTH`).
2. At least one uppercase Latin letter (`[A-Z]`).
3. At least one lowercase Latin letter (`[a-z]`).
4. At least one numerical digit (`[0-9]`).
5. At least one special symbol (`[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\/~`';]`).
6. Zero passwords stored in plaintext or logged in server telemetry.

---

## 3. Cryptographic JWT Token Architecture

### Token Specification
- **Algorithm**: HMAC-SHA256 (`HS256`).
- **Signature Key**: Cryptographically random 256-bit secret (`SECRET_KEY`).
- **Expiration Policy**:
  - Access Token: `60 minutes` (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).
  - Refresh Token: `7 days` (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`).

### Mandatory RFC 7519 Claims

| Claim | Key | Description | Example |
| :--- | :--- | :--- | :--- |
| **Subject** | `sub` | Unique User UUID | `"68ee188d-d6a0-4aec-a067-d5cef7f6e80e"` |
| **Issuer** | `iss` | Issuing Authority | `"cloudsage-auth"` |
| **Audience** | `aud` | Intended Recipient API | `"cloudsage-api"` |
| **Issued At** | `iat` | UNIX Timestamp of Issuance | `1731142800` |
| **Expiration** | `exp` | UNIX Timestamp of Expiration | `1731146400` |
| **JWT ID** | `jti` | Unique Random Token Identifier | `"bb063842-d263-41de-9f3f-c9efda174da0"` |
| **Role** | `role` | Primary Canonical Role | `"FINOPS_MANAGER"` |
| **Roles** | `roles` | Array of Assigned Roles | `["FINOPS_MANAGER"]` |
| **Tenant** | `tenant_id` | Organization Tenant UUID | `"52749090-4c86-4e73-89f5-ea32bf0d23a7"` |
| **Session** | `session_id` | Database Active Session UUID | `"77df5090-2c86-4e73-89f5-ea32bf0d23a7"` |

---

## 4. Single-Use Refresh Token Rotation & Anti-Replay Defense

To protect against token interception and session hijacking:
1. When a client calls `POST /api/v1/auth/refresh`, the server validates the provided refresh token and checks that its active session record is valid.
2. The server generates a brand new access token and a brand new refresh token.
3. The previous refresh token is immediately invalidated in the database (`refresh_token_hash` updated).
4. **Replay Detection**: If a malicious actor attempts to reuse an old refresh token, the hash lookup fails and the server responds with `HTTP 401 Unauthorized`.

---

## 5. Brute-Force Protection & Lockout Policy

CloudSage prevents credential stuffing and brute-force guessing attacks:
- **Max Failed Logins**: `5 attempts` (configurable via `LOGIN_MAX_FAILED_ATTEMPTS`).
- **Lockout Duration**: `15 minutes` (configurable via `LOGIN_LOCKOUT_MINUTES`).
- **Lockout Action**: When an account reaches the threshold:
  1. `is_locked` is set to `True`.
  2. `locked_until` is stamped with UTC expiration time.
  3. A `CRITICAL` severity security event (`ACCOUNT_LOCKED`) is recorded.
  4. Subsequent login attempts return `HTTP 423 Locked`.
  5. Successful login automatically resets `failed_login_attempts` to `0`.

---

## 6. Development vs. Production Header Rules
- In **Production** (`ENVIRONMENT=production`): Client headers such as `X-User-Email` and `X-User-Role` are strictly ignored. Missing or invalid Bearer JWT tokens always return `HTTP 401 Unauthorized`.
- In **Development** (`ENVIRONMENT=development` and `ALLOW_DEV_AUTH_HEADERS=true`): Controlled developer headers are accepted solely to enable automated integration test harnesses and local mocking without requiring manual JWT generation.
