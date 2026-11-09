# Investigation Workspace: Security Architecture & Compliance

## Security Principles & Advisory Mandate

The CloudSage Investigation Workspace adheres strictly to CloudSage's enterprise security architecture:

### 1. Strictly Advisory Posture
- **Zero Cloud Mutation**: The investigation engine and all associated APIs operate exclusively in **read-only** mode against cloud billing, resource inventory, and telemetry databases.
- **No Write Credentials**: The engine does not request, store, or accept cloud provider write credentials, API keys with modification permissions, or IAM roles with destructive capabilities (`ec2:TerminateInstances`, `DeleteBucket`, `SetBillingPolicy`, etc.).
- **Zero Autonomous Execution**: Recommendations and remediation playbooks generated during an investigation are strictly advisory guides for cloud engineering teams. CloudSage never deletes, terminates, downsizes, or alters cloud resources autonomously.

### 2. Strict Zero Float Rule
- Floating-point representations introduce non-deterministic rounding errors unacceptable in enterprise financial auditing.
- Every monetary amount across the investigation engine, database schema, REST API, and data structures uses Python `Decimal` and PostgreSQL `Numeric(18, 4)`.
- Rounding operations are explicitly quantized (`quantize(Decimal("0.0001"))`) to prevent cumulative drift across multi-dimensional aggregations.

### 3. Separation of Findings & Explainability
To protect against misleading diagnostic conclusions, CloudSage strictly segregates:
- `FACT`: Empirical numbers and observations extracted directly from normalized FOCUS billing line items.
- `CORRELATION`: Statistical associations between distinct telemetry signals without unproven claims of causality.
- `HYPOTHESIS`: Automated diagnostic possibilities generated via deterministic rule sets.
- `VERIFIED_CAUSE`: Manually verified or deterministically confirmed engineering causes.

---

## Access Control & Identity Architecture

### Server-Side Identity Derivation
All case transitions, assignments, notes, and finding recordings derive the authenticated user's identity from server-side security context (`AuthenticatedPrincipal`):
- Clients cannot spoof actor identity via request body fields.
- The `actor` parameter in `InvestigationService` is populated exclusively from verified authentication headers or session tokens (`get_current_principal`).

### Role-Based Access Control (RBAC) Matrix

| Endpoint Group | `VIEWER` | `ENGINEER` | `FINOPS` | `ADMIN` |
|---|:---:|:---:|:---:|:---:|
| View Stats & List Cases (`GET /investigations`) | ✓ | ✓ | ✓ | ✓ |
| View Case Detail & Analyses (`GET /investigations/{id}/*`) | ✓ | ✓ | ✓ | ✓ |
| Create Investigation Case (`POST /investigations`) | ✗ | ✓ | ✓ | ✓ |
| Add Collaboration Note (`POST /investigations/{id}/notes`) | ✗ | ✓ | ✓ | ✓ |
| Add Custom Finding (`POST /investigations/{id}/findings`) | ✗ | ✓ | ✓ | ✓ |
| Assign Case Ownership (`POST /investigations/{id}/assign`) | ✗ | ✓ | ✓ | ✓ |
| Transition Status (`POST /investigations/{id}/transition`) | ✗ | ✓ | ✓ | ✓ |
| Close / Reopen Case (`POST /investigations/{id}/close`) | ✗ | ✗ | ✓ | ✓ |

---

## Compliance & Immutable Audit Logging (SOC 2 / ISO 27001)

### Dual-Layer Audit Architecture
Every case action is captured across two distinct audit structures:

1. **`InvestigationHistory` (Domain-Specific Audit)**:
   - Tracks granular lifecycle state transitions from status to status.
   - Records notes, details dictionary (e.g., verified root cause, previous assignee), and exact timestamp.
   - Exposed to analysts directly in the case interface for operational transparency.

2. **`AuditLog` (Enterprise Security Ledger)**:
   - Immutable security record written to the centralized `audit_logs` ledger.
   - Contains:
     - `timestamp` (UTC)
     - `user_email` (authenticated actor)
     - `action_type` (`INVESTIGATION_CREATE`, `INVESTIGATION_ASSIGN`, `INVESTIGATION_TRANSITION`, `INVESTIGATION_CLOSE`, `INVESTIGATION_REOPEN`)
     - `resource_type` (`"investigation_cases"`)
     - `resource_id` (case UUID)
     - `before_state` (JSON prior state)
     - `after_state` (JSON updated state)
     - `status` (`SUCCESS` / `FAILURE`)
   - Meets SOC 2 Common Criteria (CC6.1, CC6.8) and ISO/IEC 27001 control requirements for non-repudiation and privileged activity tracking.

### Immutable Evidence Links
When an investigation is opened, the system creates `InvestigationEvidenceLink` records capturing:
- Entity type (`cost_anomalies`, `billing_records`, `cloud_resources`, `waste_detections`, `recommendations`, `alert_instances`).
- Entity ID and relationship role (`PRIMARY_ANOMALY`, `TRIGGERING_ALERT`, `CONTRIBUTING_BILLING_LINE_ITEM`).
- Point-in-time JSON metadata snapshot, preventing retroactive mutation of historical evidence even if upstream cloud resources are subsequently terminated or deleted.
