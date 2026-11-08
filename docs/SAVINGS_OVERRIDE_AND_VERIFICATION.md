# Savings Override & Financial Verification Governance

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Overview

Automated cloud cost engines calculate theoretical savings based on list prices or static discount models. However, real-world enterprise architectures often involve:
- Partial rightsizing constraints (e.g., memory overhead requirements requiring a larger SKU than pure CPU metrics suggest).
- Reserved Instance (RI) or Savings Plans portfolio blending.
- Negotiated custom Enterprise Discount Programs (EDP).
- Implementation labor costs or migration overhead.

To prevent inaccurate financial reporting, Stage 11 implements a **Two-Phase Savings Override Governance Workflow**. This empowers engineers to propose realistic savings adjustments while requiring FinOps lead approval before revised figures impact executive reporting.

---

## 2. Two-Phase Governance Lifecycle

```
[ Algorithmic Recommendation Created ]
      Original Savings: $150.00/mo
                   │
                   ▼
       [ Phase 1: Proposal ]
Engineer proposes revised savings: $95.00/mo
with mandatory justification notes
Status: PENDING
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
[ Phase 2A: Approval ]   [ Phase 2B: Rejection ]
FinOps Lead Approves     FinOps Lead Rejects
- Status: APPROVED       - Status: REJECTED
- is_savings_overridden=True - Recommendation keeps
- revised_monthly_savings=$95 original savings figure
```

---

## 3. Database Schema: `recommendation_savings_overrides`

Defined in `backend/app/models/recommendation.py` and provisioned via migration `009_recommendation_waste_workspace.py`:

```sql
CREATE TABLE recommendation_savings_overrides (
    id UUID PRIMARY KEY,
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    original_monthly_savings NUMERIC(18, 4) NOT NULL,
    proposed_monthly_savings NUMERIC(18, 4) NOT NULL,
    reason TEXT NOT NULL,
    proposed_by VARCHAR(255) NOT NULL,
    approved_by VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE
);
```

### Constraints & Financial Integrity:
- **Strict Zero Float Rule:** All savings figures are stored as `NUMERIC(18, 4)` and handled via Python `Decimal`. Floating-point values are rejected.
- **Non-Negative Validation:** Proposed savings must be greater than or equal to `Decimal("0.0000")`. Negative savings proposals return an HTTP 400 validation error.
- **Audit Immobility:** Override history is permanent; rejected or approved records cannot be deleted.

---

## 4. Impact on Financial KPI Rollups

When a savings override is approved:
1. `recommendation.is_savings_overridden` is set to `True`.
2. `recommendation.revised_monthly_savings` is set to `proposed_monthly_savings`.
3. Financial analytics and dashboard rollups use `revised_monthly_savings` in place of `estimated_monthly_savings` for aggregate potential savings totals.
4. Executive reporting clearly indicates that the figure has been human-verified and approved by FinOps leadership.

---

## 5. REST API Workflow

### 1. Propose Savings Override
`POST /api/v1/recommendations/{id}/override`
```json
{
  "proposed_monthly_savings": 95.00,
  "reason": "Production database requires 32GB RAM minimum; rightsizing limited to db.r5.xlarge instead of db.m5.large.",
  "proposed_by": "db-admin@company.com"
}
```

### 2. List Overrides for Recommendation
`GET /api/v1/recommendations/{id}/overrides`
Returns historical list of all override proposals and their review outcomes.

### 3. Review / Approve / Reject Override
`POST /api/v1/recommendations/{id}/override/{override_id}/approve`
```json
{
  "approved": true,
  "reviewed_by": "finops-director@company.com",
  "notes": "Verified against production RDS memory benchmarks. Approved."
}
```
If `approved` is `false`, a mandatory `rejection_reason` must be provided.
