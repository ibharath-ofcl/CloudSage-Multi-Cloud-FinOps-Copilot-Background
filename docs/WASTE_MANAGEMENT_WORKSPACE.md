# Enterprise Waste Management Workspace

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Overview

The **Enterprise Waste Management Workspace** equips FinOps operators and platform engineers with specialized tools to detect, investigate, triage, and remediate cloud waste findings across multi-cloud environments (AWS, Azure, GCP).

Waste findings identify completely unutilized or orphaned cloud assets that incur non-zero monthly recurring costs without delivering business value. The workspace transforms raw waste detections from Stage 6 into actionable, trackable remediation work streams.

Key features include:
- **Root Cause & Evidence Inspection:** Clear explanation of why the resource was flagged as waste (e.g., zero read/write IOPS for 14 days, network interface unattached, idle database).
- **Comprehensive Lifecycle Triage:** Explicit status actions including `ACKNOWLEDGE`, `ASSIGN`, `SNOOZE`, `DISMISS`, `RESOLVE`, and `REOPEN`.
- **Bulk Action Capabilities:** Perform batch triage across dozens of waste items simultaneously with isolated error handling.
- **Remediation Playbook Generation:** Generate provider-specific CLI commands, Terraform definitions, and CloudFormation/Bicep templates for decommissioning waste safely.
- **Audit Logging:** Every status change, assignment, snoozing window, and resolution note is permanently recorded for regulatory and financial audit compliance.

---

## 2. Waste Finding Lifecycle State Machine

The waste lifecycle guarantees full accountability from detection through remediation:

```
                  ┌──────────────┐
                  │   DETECTED   │
                  └──────┬───────┘
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      ┌──────────────┐        ┌──────────────┐
      │ ACKNOWLEDGED │        │  DISMISSED   │
      └──────┬───────┘        └──────────────┘
             │                       ▲
     ┌───────┴───────┐               │
     ▼               ▼               │
┌──────────┐   ┌───────────┐         │
│ ASSIGNED │   │  SNOOZED  ├─────────┘
└────┬─────┘   └─────┬─────┘
     │               │
     └───────┬───────┘
             ▼
      ┌──────────────┐
      │   RESOLVED   │
      └──────┬───────┘
             │ (Reopen if reappears)
             ▼
      ┌──────────────┐
      │  REOPENED    │
      └──────────────┘
```

### Lifecycle Actions & Rules:

1. **ACKNOWLEDGE:** Confirms that the finding has been reviewed by the FinOps team and is queued for action.
2. **ASSIGN:** Assigns the finding to a specific engineer or team (`assigned_to`) along with optional action notes.
3. **SNOOZE:** Postpones the finding until a specified date (`snooze_until`), suppressing alert noise during maintenance windows or migration periods.
4. **DISMISS:** Closes the finding as a false positive or acceptable operational cost. **Requires a mandatory justification reason.**
5. **RESOLVE:** Marks the finding as remediated (e.g., resource deleted or reattached). **Requires a mandatory resolution reason** and records `resolved_by` and `resolved_at`.
6. **REOPEN:** Reopens a resolved or dismissed finding if the resource is still accumulating waste. Records `reopened_by` and `reopened_at`.

---

## 3. Architecture & API Endpoints

### Database Schema Additions (`backend/app/models/waste.py`):

The `WasteDetection` table was updated via migration `009_recommendation_waste_workspace.py` with enterprise operational columns:

| Column | Type | Description |
|---|---|---|
| `assigned_to` | `VARCHAR(255)` | Email or username of the assigned owner. |
| `resolved_by` | `VARCHAR(255)` | Actor who resolved the finding. |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Timestamp when resolution occurred. |
| `reopened_by` | `VARCHAR(255)` | Actor who reopened the finding. |
| `reopened_at` | `TIMESTAMP WITH TIME ZONE` | Timestamp when finding was reopened. |
| `action_notes` | `TEXT` | Operational context or audit commentary. |

### REST Endpoints (`backend/app/api/routes/waste_detection.py`):

- `GET /api/v1/waste/findings`: List findings with filtering by provider, waste type, status, minimum cost, and owner.
- `POST /api/v1/waste/findings/{id}/action`: Execute lifecycle transitions (`ACKNOWLEDGE`, `ASSIGN`, `SNOOZE`, `DISMISS`, `RESOLVE`, `REOPEN`).
- `POST /api/v1/waste/batch`: Execute atomic batch lifecycle actions with partial failure isolation.
- `GET /api/v1/waste/findings/{id}/investigation`: Comprehensive investigation payload linking resource details, telemetry metrics, and financial breakdown.
- `GET /api/v1/waste/findings/{id}/telemetry`: 14-day/30-day time-series telemetry for the flagged asset.
- `GET /api/v1/waste/findings/{id}/playbook`: Generate advisory remediation playbook in 7 formats.
- `GET /api/v1/waste/findings/{id}/playbook/download`: Direct file download of remediation scripts.

---

## 4. Investigation Drawer & Telemetry Verification

Before an engineer executes a decommissioning script on an orphaned resource, they must verify operational inactivity. The Investigation Drawer provides:

1. **Detection Rule Evidence:** Why the rule fired (e.g., `IdleComputeRule`: Average CPU utilization < 2.5% over 14 continuous days).
2. **Telemetry Validation:** Visual inspection of actual CPU, Memory, Network, and Disk IOPS time-series curves.
3. **Financial Impact:** Exact monthly waste cost calculated using `Decimal` arithmetic based on normalized billing records.
4. **Remediation Script:** Pre-generated, non-destructive CLI or IaC scripts to safely clean up the asset with explicit rollback instructions.
5. **Audit Trail:** History of when the finding was detected, acknowledged, assigned, or modified.

---

## 5. Frontend Implementation

The frontend workspace (`frontend/src/pages/WastePage.tsx`) provides:
- **Interactive Waste Table:** Checkbox selection, severity badges, waste category icons, financial waste values, and quick action buttons.
- **Batch Action Toolbar:** Floats into view when items are selected, allowing one-click bulk acknowledgment, assignment, snoozing, or resolution.
- **Triage Action Modal:** Dynamically prompts for required fields (e.g., justification for dismissal, snooze days for snoozing, owner for assignment).
- **Remediation Drawer:** Renders the 7-format playbook viewer and time-series telemetry chart side-by-side with investigation notes.
