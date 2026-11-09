# CloudSage Fine-Grained Permission Matrix

## 1. Overview
The CloudSage permission taxonomy follows the standardized `resource:action` format. Every API route checks for required permissions via FastAPI dependencies.

---

## 2. Master Permission Matrix

| Permission Code | Domain / Description | SUPER_ADMIN | ORG_ADMIN | FINOPS_MGR | FINOPS_ANALYST | CLOUD_ENG | SEC_AUDITOR | VIEWER |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `*` | Full Platform Wildcard | **YES** | NO | NO | NO | NO | NO | NO |
| `dashboard:read` | View FinOps Overview & Visualizations | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** |
| `dashboard:export` | Export CSV/JSON Reports | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `billing:read` | Read Ingestion & Normalization Ledgers | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** |
| `billing:export` | Export Normalized Cost Data | **YES** | **YES** | **YES** | **YES** | NO | NO | NO |
| `resources:read` | View Multi-Cloud Resource Inventory | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `resources:sync` | Trigger Provider Resource Discovery Sync | **YES** | **YES** | **YES** | NO | **YES** | NO | NO |
| `waste:read` | View Idle & Abandoned Waste Candidates | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `waste:update` | Update Waste Detection Metadata | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `waste:dismiss` | Dismiss Waste Finding with Reason | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `recommendations:read` | View Advisory FinOps Recommendations | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `recommendations:update` | Edit Recommendation Implementation Notes | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `recommendations:approve` | Approve Recommendation Execution | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `recommendations:dismiss` | Dismiss or Reject Recommendation | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `recommendations:override` | Override Financial Savings Estimates | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `anomalies:read` | View Statistical Cost Anomalies | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `anomalies:dismiss` | Mark Anomaly as False Positive / Dismiss | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `investigations:create` | Open RCA Investigation Workspace Case | **YES** | **YES** | **YES** | **YES** | NO | NO | NO |
| `investigations:read` | View Investigation Findings & Evidence | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | NO |
| `investigations:update` | Add Notes, Hypotheses, and Evidence | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `investigations:assign` | Reassign Investigation Lead / Owner | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `investigations:resolve` | Mark Investigation Root Cause Identified | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `investigations:close` | Formally Close Investigation Case | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `investigations:reopen` | Reopen Closed Investigation Case | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `alerts:read` | View Fired Alerts & Alert History | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | NO |
| `alerts:manage` | Create, Edit, or Delete Alert Rules | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `alerts:acknowledge` | Acknowledge Alert Instance Triage | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `alerts:resolve` | Resolve Alert Incident | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `notifications:read` | View Notification Feed & Deliveries | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** | **YES** |
| `notification_rules:manage` | Configure Alert Routing & Preferences | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `copilot:query` | Natural Language FinOps Copilot Chat | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `users:read` | List Organizational Users & Profiles | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `users:manage` | Provision, Edit, or Deactivate Users | **YES** | **YES** | NO | NO | NO | NO | NO |
| `sessions:revoke` | Revoke Active User Sessions Immediately | **YES** | **YES** | NO | NO | NO | NO | NO |
| `roles:read` | View Roles & Permission Matrix Catalog | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `roles:manage` | Assign Roles & Manage Custom Policies | **YES** | **YES** | NO | NO | NO | NO | NO |
| `audit:read` | Inspect Immutable Audit Logs | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `audit:export` | Export Audit Ledger for Compliance | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `audit:verify` | Run SHA-256 Hash Chain Verification | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `security:read` | View Threat Telemetry & Security Events | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `security:manage` | Configure Lockouts & Security Policies | **YES** | **YES** | NO | NO | NO | NO | NO |
| `tenant:read` | Inspect Tenant Configuration & Domain | **YES** | **YES** | NO | NO | NO | **YES** | NO |
| `tenant:manage` | Update Organization Security Policies | **YES** | **YES** | NO | NO | NO | NO | NO |
| `approvals:request` | Submit Action for Dual-Party Approval | **YES** | **YES** | **YES** | **YES** | **YES** | NO | NO |
| `approvals:decide` | Approve or Reject Dual Approval Request | **YES** | **YES** | **YES** | NO | NO | NO | NO |
| `playbooks:generate` | Generate Remediation Playbooks | **YES** | **YES** | **YES** | NO | **YES** | NO | NO |

---

## 3. High-Privilege Operation Restrictions
1. **SUPER_ADMIN Provisioning**: Even an `ORGANIZATION_ADMIN` cannot provision or assign a user to `SUPER_ADMIN`. Attempting to do so triggers a `PRIVILEGE_ESCALATION_ATTEMPT` security event.
2. **Self-Deactivation Prevention**: An administrator cannot deactivate their own active user account.
3. **Dual Approval Requirement**: Critical operations (such as security policy mutation or break-glass access) require two distinct individuals (`requester != approver`).

