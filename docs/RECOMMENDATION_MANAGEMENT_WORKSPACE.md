# Enterprise Recommendation Management Workspace

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Overview

The **Enterprise Recommendation Management Workspace** serves as the central operational hub for FinOps practitioners, engineering leads, and cloud financial administrators to triage, investigate, govern, and act upon cost-saving recommendations across AWS, Microsoft Azure, and Google Cloud Platform.

Building on the Stage 8 advisory recommendation engine, Stage 11 elevates recommendations from passive analytical findings into an active, governed enterprise workflow. The workspace combines:

- **Multi-Factor Triage & Filtering:** Rapid identification of high-impact opportunities sorted by net monthly savings, implementation effort, confidence score, risk level, or lifecycle stage.
- **Deep Entity Correlation:** Contextual drill-down linking each recommendation to its underlying cloud resource, associated waste detections, cost anomalies, historical billing records, and time-series utilization metrics.
- **Governed Review Workflows:** Granular status transitions (Approve, Reject, Snooze, Dismiss, Implement) with mandatory justification capture, owner assignment, and external ITSM/ticketing system references.
- **Financial Governance & Overrides:** Two-phase proposal and approval workflows for revising estimated savings based on real-world architecture constraints.
- **Advisory Remediation Playbooks:** Automated generation of non-destructive infrastructure-as-code and CLI scripts across 7 formats with rollback safety plans.

---

## 2. Architecture & Component Hierarchy

```
┌────────────────────────────────────────────────────────────────────────┐
│                   RecommendationsPage (React Workspace)                │
├────────────────────────────────────────────────────────────────────────┤
│  Top Metrics Header (Actionable Recommendations, Total Pipeline, etc.) │
│  Filter & Search Bar (Provider, Status, Priority, Strategy, Text)       │
│  Batch Action Bar (Approve, Snooze, Dismiss Selected Recommendations)   │
├──────────────────────────────────┬─────────────────────────────────────┤
│      Recommendation Table        │       Detail Drawer / Panel         │
│  - Multi-select Checkboxes       │  - Overview & Financial Impact      │
│  - Priority Badge (P1-P4)        │  - Resource Telemetry Chart (SVG)   │
│  - Title & Action Summary        │  - Entity Correlation Matrix        │
│  - Cloud Provider (AWS/Azure/GCP)│  - Savings Override Manager         │
│  - Monthly Savings ($)           │  - Remediation Playbook Generator   │
│  - Status & Assigned Owner       │  - Chronological Audit Timeline     │
│  - Action Buttons (Review/Detail)│  - Action Buttons (Approve/Reject)  │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### Backend Components

1. **API Router (`backend/app/api/routes/recommendations.py`):**
   - `GET /api/v1/recommendations`: Multi-factor search, sorting, and filtering.
   - `GET /api/v1/recommendations/{id}`: Detailed recommendation metadata with evidence.
   - `POST /api/v1/recommendations/{id}/action`: Individual review transitions with audit logging.
   - `POST /api/v1/recommendations/batch`: Atomic batch reviews with transaction savepoint isolation.
   - `POST /api/v1/recommendations/{id}/override`: Two-phase savings override proposal.
   - `GET /api/v1/recommendations/{id}/overrides`: Savings override audit trail.
   - `POST /api/v1/recommendations/{id}/override/{override_id}/approve`: Approver sign-off on revised savings.
   - `GET /api/v1/recommendations/{id}/telemetry`: 14-day/30-day time-series telemetry metrics.
   - `GET /api/v1/recommendations/{id}/correlations`: Multi-entity correlation matrix with anti-double-counting guarantees.
   - `GET /api/v1/recommendations/{id}/playbook`: 7-format advisory remediation playbook generator.
   - `GET /api/v1/recommendations/{id}/playbook/download`: Direct script download with MIME types.

2. **Lifecycle Service (`backend/app/recommendations/lifecycle.py`):**
   - Validates state transitions against the `RecommendationStatus` state machine.
   - Enforces justification requirements for rejections and dismissals.
   - Manages owner assignments, external ticket references, and snooze expiration timestamps.
   - Records state history in `recommendation_history`.

3. **Data Models (`backend/app/models/recommendation.py`):**
   - `Recommendation`: Extended with `snooze_until`, `assigned_to`, `external_ticket_ref`, `revised_monthly_savings`, `is_savings_overridden`.
   - `RecommendationSavingsOverride`: Historical audit records for savings adjustments.

---

## 3. Triage & Filtering Engine

The workspace supports rich querying to assist administrators in prioritizing high-value savings:

| Filter Parameter | Type | Description |
|---|---|---|
| `provider` | `str` | Filters by `AWS`, `AZURE`, or `GCP`. |
| `status` | `str` | Filters by lifecycle status (`PROPOSED`, `UNDER_REVIEW`, `APPROVED`, etc.). |
| `priority` | `str` | Filters by priority (`P1`, `P2`, `P3`, `P4`). |
| `strategy` | `str` | Filters by strategy (`RIGHTSIZING`, `IDLE_RESOURCES`, `STORAGE_OPTIMIZATION`, etc.). |
| `assigned_to` | `str` | Filters by assigned engineer or team email. |
| `min_savings` | `Decimal` | Minimum monthly savings threshold (enforces Zero Float Rule). |
| `search` | `str` | Substring match against recommendation title, description, or external ticket reference. |
| `sort_by` | `str` | Sort key: `savings_desc` (default), `savings_asc`, `priority`, `effort`, `confidence`. |

---

## 4. Entity Correlation & Evidence Grounding

Every recommendation in the workspace connects directly to supporting evidence:

1. **Target Cloud Resource:** Exact ARN, resource ID, resource type, region, account, and current operational state.
2. **Waste Detections:** Identifies if the recommendation was generated from an orphaned disk, unattached IP, or idle compute finding.
3. **Cost Anomalies:** Surfaces whether recent cost spikes triggered the optimization recommendation.
4. **Billing Line Items:** Pulls reconciled line items from the multi-cloud billing database proving actual expenditure.
5. **Time-Series Telemetry:** 14-day min/max/average CPU, Memory, Network, and Disk metrics validating that the resource is indeed underutilized before rightsizing.

---

## 5. User Interface Specifications

The frontend (`frontend/src/pages/RecommendationsPage.tsx`) provides an intuitive, responsive user experience:

- **Quick Action Modals:** Approve, Reject, Snooze, and Propose Overrides without leaving the workspace.
- **Contextual Side Drawer:** Slide-out drawer with tabbed navigation:
  - *Details & Financials:* Key metrics, priority, implementation effort, and risk analysis.
  - *Telemetry:* Interactive SVG utilization chart with metric switching (CPU, Memory, Network, Disk).
  - *Playbooks:* Multi-format code viewer with syntax highlighting, clipboard copy, and download.
  - *Correlations:* Linked resources, anomalies, waste detections, and anti-double-counting financial ledger.
  - *Audit History:* Chronological log of state transitions and human comments.
- **Bulk Action Toolbar:** Select multiple recommendations across providers and apply unified triage actions.
