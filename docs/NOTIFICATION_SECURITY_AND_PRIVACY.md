# CloudSage Notification Security, SSRF Defenses & Privacy Architecture

## 1. Overview

Because the Notification Hub accepts outbound webhook endpoints, executes network requests, and records user lifecycle actions, robust security controls are required. CloudSage enforces server-side identity derivation, Server-Side Request Forgery (SSRF) defenses, strict role-based access control (RBAC), and immutable audit trails.

---

## 2. Server-Side Identity Derivation

In earlier stages, operational endpoints accepted an optional `actor: str` field in the JSON request body. In Stage 12, this practice has been audited and replaced:

1. **Server-Derived Principals**: Identity is derived exclusively on the server via `get_authenticated_principal(request, db)` using verified Authorization Bearer tokens, gateway headers (`X-User-Email`, `X-User-Role`), or session credentials.
2. **Rejection of Client-Supplied Identities**: User emails and roles provided directly in request payloads are ignored. The server authenticates the caller, validates active account status against the `users` table, and verifies authorization roles.
3. **Role Enforcement**:
   - Creating, modifying, toggling, or deleting alert rules requires `ADMIN` or `FINOPS_ADMIN` privileges (`require_admin_or_finops_role`).
   - Viewing rules, inspecting alerts, acknowledging tickets, and configuring personal preferences are accessible to authenticated FinOps engineers.
   - Non-administrative roles attempting rule mutations receive `HTTP 403 Forbidden`.

---

## 3. Webhook SSRF Defenses (`validate_webhook_url`)

Custom webhook URLs present a significant risk of Server-Side Request Forgery (SSRF) if attackers attempt to probe internal microservices, private VPC subnets, or cloud metadata endpoints. CloudSage implements strict URL parsing and IP filtering in `backend/app/alerts/security.py`:

```mermaid
flowchart TD
    URL[Candidate Webhook URL] --> Scheme{Scheme == http/https?}
    Scheme --> |No (e.g. ftp, file)| Reject[HTTP 400 Bad Request]
    Scheme --> |Yes| Hostname[Extract FQDN / Hostname]
    
    Hostname --> DNS[Resolve Hostname via DNS]
    DNS --> |Resolution Failure| Reject
    
    DNS --> IP{Evaluate Resolved IP}
    IP --> |127.0.0.0/8 Loopback| Reject
    IP --> |10.0.0.0/8 Private RFC 1918| Reject
    IP --> |172.16.0.0/12 Private RFC 1918| Reject
    IP --> |192.168.0.0/16 Private RFC 1918| Reject
    IP --> |169.254.169.254 Cloud Metadata| Reject
    IP --> |Public Non-Reserved IP| Approve[Accept Validated Endpoint]
```

### Prohibited Destinations:
- **Cloud Metadata Services**: `169.254.169.254` (AWS IMDS, GCP metadata, Azure instance metadata) is permanently blocked to prevent credential theft.
- **Loopback Subnets**: `127.0.0.0/8` and `::1`.
- **Private Subnets**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
- **Carrier-Grade NAT & Link-Local**: `100.64.0.0/10`, `169.254.0.0/16`.

---

## 4. Immutable Audit Ledger

All administrative and operational actions are recorded in immutable audit tables:
- **Rule Mutations**: Every create, update, toggle, and soft-delete logs an `AuditLog` entry with `action_type` (`ALERT_RULE_CREATE`, `ALERT_RULE_UPDATE`, `ALERT_RULE_DELETE`), `user_email`, timestamp, and before/after state diffs.
- **Alert State Machine Transitions**: Every lifecycle transition (`ACKNOWLEDGE`, `INVESTIGATE`, `RESOLVE`, `SUPPRESS`, `ESCALATE`) logs an `AlertHistory` record with `from_status`, `to_status`, `actor`, and mandatory operator notes.
- **Outbox Attempt Logging**: Every delivery attempt logs an immutable `NotificationDeliveryAttempt` entry with execution latency, response codes, and sanitized error messages.

---

## 5. Data Privacy & Advisory Containment

- **Payload Sanitization**: Webhook payloads contain cloud account IDs, service names, and aggregate spend metrics. Customer proprietary data, IAM secret keys, and personal identifiable information (PII) are never included in outbound alerts.
- **Advisory Containment**: Outbound notifications are strictly informative. CloudSage will never trigger automated infrastructure deletion or resource changes from an alert.
