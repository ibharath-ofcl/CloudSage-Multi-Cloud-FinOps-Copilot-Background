# CloudSage Multi-Tenant Data Isolation & IDOR Protection

## 1. Overview
CloudSage is architected to support enterprise multi-tenancy, providing strict cryptographic and logical boundaries between distinct corporate organizations, business units, or clients. Data belonging to Tenant A is never accessible to, visible to, or leakable to Tenant B.

---

## 2. Multi-Tenant Boundary Architecture

```
                    ┌────────────────────────────┐
                    │     HTTP Client Request    │
                    │   (Authorization: Bearer)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │  Cryptographic JWT Decode  │
                    │ (sub, email, role, tenant) │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │   AuthenticatedPrincipal   │
                    │  (tenant_id = UUID_Acme)   │
                    └─────────────┬──────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
        ▼                                                   ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     TenantContext.scope_query   │       │ TenantContext.verify_tenant_acc │
│ (query.filter(model.tenant_id)) │       │ (Raises 403 on IDOR Mismatch)   │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 ▼                                         ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│       Database Query            │       │      Threat Event Logged        │
│    (Tenant A Records ONLY)      │       │  (CROSS_TENANT_ACCESS_DENIED)   │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

---

## 3. Enforcement Layers

### Layer 1: Query Scoping via `TenantContext.scope_query`
Every database query operating on tenant-aware entities automatically applies tenant filtering:
```python
def scope_query(query: Query, model: Any, principal: AuthenticatedPrincipal) -> Query:
    if principal.is_super_admin:
        return query

    if hasattr(model, "tenant_id"):
        if principal.tenant_id:
            tenant_uuid = UUID(str(principal.tenant_id))
            return query.filter(model.tenant_id == tenant_uuid)
        else:
            # Unassigned caller gets zero records safely
            return query.filter(False)

    return query
```

### Layer 2: Insecure Direct Object Reference (IDOR) Protection
When an endpoint receives a specific resource ID in a URL path (e.g. `GET /api/v1/admin/users/{user_id}` or `POST /api/v1/admin/security/approvals/{id}/decide`), CloudSage explicitly verifies that the requested entity belongs to the principal's tenant:
```python
TenantContext.verify_tenant_access(principal, user.tenant_id)
```
If `user.tenant_id != principal.tenant_id`, the request immediately halts with:
`HTTP 403 Forbidden: "Access denied: Cross-tenant data access is strictly forbidden."`

### Layer 3: Security Telemetry & Probing Detection
Whenever a cross-tenant access attempt occurs, `ThreatDetectionService` records an event:
- **Event Type**: `CROSS_TENANT_ACCESS_DENIED`
- **Severity**: `HIGH`
- **Details**: Captures caller IP, authenticated user email, source tenant ID, target tenant ID, and endpoint.

---

## 4. Super Admin Global Visibility Exception
Only principals with the `SUPER_ADMIN` role (`is_super_admin=True`) possess platform-wide inspection rights. Super admins can query across all tenants or supply an explicit `tenant_id` query parameter to inspect specific organizations during support or onboarding workflows.
