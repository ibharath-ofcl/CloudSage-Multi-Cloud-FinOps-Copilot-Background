# CloudSage RBAC Architecture & Enterprise Role Taxonomy

## 1. Overview
CloudSage implements a canonical 7-tier Role-Based Access Control (RBAC) hierarchy designed for large enterprise organizations with complex FinOps operational models. Access is governed by least-privilege principles, where each role maps to an explicit set of `resource:action` capabilities.

---

## 2. The 7 Canonical Enterprise Roles

```
               [ SUPER_ADMIN ]  (Global Platform Authority / Wildcard "*")
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
[ ORGANIZATION_ADMIN ]    [ SECURITY_AUDITOR ]
(Tenant Boundary Admin)   (Read-Only Audit & Security Logs)
           │
           ▼
   [ FINOPS_MANAGER ]
   (Approve Recommendations, Alert Rules Governance)
           │
     ┌─────┴──────────────┐
     ▼                    ▼
[ FINOPS_ANALYST ]   [ CLOUD_ENGINEER ]
(Triage Anomalies,   (Inventory & Playbooks)
 Findings & Drafts)
     │
     ▼
  [ VIEWER ]
  (Read-Only High-Level Dashboards)
```

### Detailed Role Descriptions

| Role Name | Scope | Description | Core Capabilities |
| :--- | :--- | :--- | :--- |
| **SUPER_ADMIN** | Global (Cross-Tenant) | System administrator with unrestricted platform authority. | Full wildcard (`*`) access to all endpoints, tenants, and configurations. |
| **ORGANIZATION_ADMIN** | Single Tenant | Tenant administrator managing users, cloud accounts, integrations, alert rules, and security policies. | User administration, role inspection, tenant policy management, full FinOps access within tenant. |
| **FINOPS_MANAGER** | Single Tenant | Financial operations lead with authority to approve recommendations, assign investigations, and govern alert rules. | Recommendation approval, investigation closure, notification rule management, alert triage. |
| **FINOPS_ANALYST** | Single Tenant | Financial analyst investigating anomalies, authoring findings, and evaluating waste opportunities. | Cost trend analysis, anomaly investigation, recommendation drafting (cannot approve recommendations). |
| **CLOUD_ENGINEER** | Single Tenant | Technical engineer inspecting cloud resource telemetry, reviewing hardware metrics, and generating remediation playbooks. | Resource inventory, waste detection, infrastructure playbook generation. |
| **SECURITY_AUDITOR** | Single Tenant | Compliance officer inspecting audit logs, security events, authentication records, and hash chain integrity. | Read-only audit ledgers, hash chain verification, security event inspection (cannot modify FinOps data). |
| **VIEWER** | Single Tenant | Executive or stakeholder needing high-level visibility without operational authority. | Read-only access to executive overview dashboards and cost reports. |

---

## 3. Backward Compatibility with Legacy Roles

CloudSage seamlessly maps legacy stage roles to the enterprise taxonomy:

| Legacy Role | Canonical Enterprise Role Equivalent | Notes |
| :--- | :--- | :--- |
| `FINOPS_ENGINEER` | `FINOPS_MANAGER` | Retains full approval authority for recommendations and alerts. |
| `FINANCE_ANALYST` | `FINOPS_ANALYST` | Retains analytical and investigation authoring rights. |
| `ENGINEERING_MANAGER` | `FINOPS_MANAGER` | Full operational approval rights within engineering department. |
| `EXECUTIVE` | `VIEWER` | High-level summary dashboard views without modification rights. |

---

## 4. Enforcement Mechanics

Role and permission enforcement is implemented strictly on the server side:

```python
# 1. Fine-Grained Permission Check
@router.post("/recommendations/{id}/approve")
def approve_recommendation(
    id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.RECOMMENDATIONS_APPROVE)),
    db: Session = Depends(get_sync_db),
):
    ...

# 2. Role Check
@router.get("/admin/security/stats")
def get_security_stats(
    principal: AuthenticatedPrincipal = Depends(
        require_role(UserRole.SUPER_ADMIN.value, UserRole.SECURITY_AUDITOR.value, UserRole.ORGANIZATION_ADMIN.value)
    ),
    db: Session = Depends(get_sync_db),
):
    ...
```

Frontend gates (`PermissionGate`, `RoleGate`, `ProtectedRoute`) provide responsive user experiences by hiding unavailable UI controls, but are never relied upon for security boundaries.
