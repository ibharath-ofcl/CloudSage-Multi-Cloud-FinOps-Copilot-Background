# Review Lifecycle & Audit Infrastructure

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Overview

Enterprise cloud cost governance requires complete transparency and accountability. CloudSage enforces an immutable review lifecycle for both recommendations and waste detections. Every decision—whether approving a rightsizing suggestion, snoozing an idle disk alert, or rejecting an optimization proposal—is tracked with actor attribution, justification notes, external ticketing references, and precise timestamps.

---

## 2. Recommendation State Machine

The recommendation governance lifecycle is defined by the `RecommendationStatus` enumeration:

```
                  ┌──────────────┐
                  │   PROPOSED   │
                  └──────┬───────┘
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
      ┌────────────┐ ┌────────┐ ┌───────────┐
      │UNDER_REVIEW│ │SNOOZED │ │ DISMISSED │
      └──────┬─────┘ └───┬────┘ └───────────┘
             │           │
       ┌─────┴─────┐     │ (Snooze expires)
       ▼           ▼     │
  ┌──────────┐ ┌────────┐│
  │ APPROVED │ │REJECTED││
  └────┬─────┘ └────────┘│
       │                 │
       ▼                 │
┌─────────────┐          │
│ IMPLEMENTED │◄─────────┘
└─────────────┘
```

### Transition Rules & Prerequisites:

| Current Status | Target Status | Required Fields / Conditions |
|---|---|---|
| `PROPOSED` | `UNDER_REVIEW` | `actor` |
| `PROPOSED` / `UNDER_REVIEW` | `APPROVED` | `actor`, optional `assigned_to`, optional `external_ticket_ref` |
| `PROPOSED` / `UNDER_REVIEW` | `REJECTED` | `actor`, **mandatory `notes` / justification reason** |
| `PROPOSED` / `UNDER_REVIEW` | `SNOOZED` | `actor`, **mandatory `snooze_days` $\ge 1$** (computes `snooze_until`) |
| `ANY` (except `IMPLEMENTED`) | `DISMISSED` | `actor`, **mandatory `notes` / justification reason** |
| `APPROVED` | `IMPLEMENTED` | `actor`, optional `external_ticket_ref` |

---

## 3. Database Audit Logging

Whenever a recommendation changes state, a new record is appended to the `recommendation_history` table:

```sql
CREATE TABLE recommendation_history (
    id UUID PRIMARY KEY,
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    previous_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Invariants Maintained:
1. **Append-Only:** Historical records are never modified or deleted.
2. **Actor Attribution:** Every state transition requires an explicit identity (e.g., `finops-lead@company.com`).
3. **Reason Capture:** Critical rejections, dismissals, and overrides must include detailed context for auditability.

---

## 4. Atomic Batch Operations with Transaction Savepoints

Enterprise operators often triage dozens of recommendations at once. If an operator approves 50 items and item #32 fails due to a validation error, standard database transactions would either rollback all 50 items or corrupt session state.

CloudSage solves this using **SQLAlchemy nested transactions (SAVEPOINTS)**:

```python
results = []
success_count = 0
failure_count = 0

for rec_id in request.recommendation_ids:
    try:
        # Create an isolated savepoint for each item
        with db.begin_nested():
            rec = transition_recommendation_status(
                db=db,
                recommendation_id=rec_id,
                new_status=new_status,
                actor=request.actor,
                notes=request.notes,
                snooze_days=request.snooze_days,
                assigned_to=request.assigned_to,
                external_ticket_ref=request.external_ticket_ref,
                auto_commit=False, # Flushed inside savepoint
            )
            results.append({"id": str(rec_id), "status": "SUCCESS"})
            success_count += 1
    except Exception as exc:
        results.append({"id": str(rec_id), "status": "FAILED", "error": str(exc)})
        failure_count += 1

# Commit all successful items at once
db.commit()
```

### Guarantees:
- **Partial Failure Isolation:** An error on one recommendation does not abort the entire batch.
- **Atomic Persistence:** All successful transitions commit cleanly together.
- **Transparent Feedback:** The API returns individual success/failure statuses for every ID in the batch.

---

## 5. External ITSM / Ticketing Integration

Recommendations can be tied directly to corporate ticketing systems (Jira, ServiceNow, Linear) via the `external_ticket_ref` field (e.g., `FINOPS-1042`, `INC-99412`).

- Searchable directly in the workspace search bar.
- Displayed prominently in the UI table and detail drawer.
- Included in generated remediation playbooks and audit timelines.
