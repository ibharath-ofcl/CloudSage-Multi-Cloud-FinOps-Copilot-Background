# Investigation & Root Cause Analysis REST API Reference

## Base Path: `/api/v1/investigations`

All endpoints require authentication via Bearer token or session headers (`X-User-Role`, `X-User-Email`). All monetary amounts are formatted with 4 decimal places (`Numeric(18, 4)` / `Decimal`).

---

## 1. Statistics & Case Management

### `GET /api/v1/investigations/stats`
Retrieves global Key Performance Indicators (KPIs) for the investigation workspace.
- **Roles**: `VIEWER`, `FINOPS`, `ENGINEER`, `ADMIN`
- **Response**: `InvestigationStatsResponse`
```json
{
  "total_investigations": 42,
  "open_investigations": 12,
  "critical_investigations": 3,
  "unassigned_investigations": 2,
  "root_cause_identified_count": 8,
  "resolved_investigations": 25,
  "total_excess_spend_investigated": "54200.7500",
  "average_investigation_age_hours": "14.25"
}
```

### `GET /api/v1/investigations`
Lists investigation cases with multi-dimensional filtering, searching, and pagination.
- **Query Parameters**:
  - `provider` (optional): `AWS`, `AZURE`, `GCP`, or `ALL`
  - `status` (optional): `NEW`, `ASSIGNED`, `INVESTIGATING`, `ROOT_CAUSE_IDENTIFIED`, `ACTION_RECOMMENDED`, `RESOLVED`, `CLOSED`
  - `priority` (optional): `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - `assigned_to` (optional): User email or `"unassigned"`
  - `service_name` (optional): Service name filter
  - `search` (optional): Case number, title, service, or resource ID substring
  - `limit` (default: 50, max: 200)
  - `offset` (default: 0)
- **Response**: `InvestigationCaseListResponse`

### `POST /api/v1/investigations`
Creates a formal investigation case from an anomaly or alert.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Request Body**: `InvestigationCaseCreate`
```json
{
  "anomaly_id": "3396715d-a6ba-4ad1-9ef1-008b730098b9",
  "alert_instance_id": "711c65a0-0000-0000-0000-000000000000",
  "title": "AWS EC2 Critical Compute Surge on us-east-1",
  "priority": "CRITICAL",
  "assigned_to": "finops-lead@cloudsage.com",
  "initial_notes": "Triage opened from high-severity alert."
}
```
- **Response**: `InvestigationCaseDetailResponse` (201 Created)

### `GET /api/v1/investigations/{id}`
Retrieves complete details for a specific investigation case, including findings, notes, evidence links, and state history.
- **Response**: `InvestigationCaseDetailResponse`

### `PATCH /api/v1/investigations/{id}`
Updates case priority, title, suspected category, or root cause summary.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Request Body**: `InvestigationCaseUpdate`

### `POST /api/v1/investigations/{id}/assign`
Assigns ownership of an investigation case to a FinOps engineer.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Request Body**:
```json
{
  "assigned_to": "alex.engineer@cloudsage.com",
  "notes": "Assigning for batch cluster investigation."
}
```

### `POST /api/v1/investigations/{id}/transition`
Transitions case lifecycle state machine with validation and audit logging.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Request Body**:
```json
{
  "target_status": "ROOT_CAUSE_IDENTIFIED",
  "verified_root_cause": "Uncapped Kubernetes CronJob parallelism in data indexing pipeline.",
  "notes": "Verified via CloudWatch and Kubernetes pod event logs."
}
```

### `POST /api/v1/investigations/{id}/close`
Formally closes an investigation case upon verification.
- **Roles**: `FINOPS`, `ADMIN`
- **Request Body**: `{"notes": "Billing stabilized and confirmed."}`

### `POST /api/v1/investigations/{id}/reopen`
Reopens a closed or resolved investigation case for further analysis.
- **Roles**: `FINOPS`, `ADMIN`
- **Request Body**: `{"notes": "Follow-up required on unattached EBS volumes."}`

---

## 2. Analytical Decomposition Endpoints

### `GET /api/v1/investigations/{id}/dimensions`
Returns 10-dimensional decomposition across FOCUS and cloud governance dimensions.
- **Response**: `MultiDimensionalAnalysisResponse`

### `GET /api/v1/investigations/{id}/contributions`
Returns Pareto 80/20 contributor ranking and cumulative contribution curves.
- **Response**: `ContributionRankingResponse`

### `GET /api/v1/investigations/{id}/usage-price-analysis`
Returns economic growth accounting ($\Delta Q \cdot P_0 + \Delta P \cdot Q_0 + \Delta Q \cdot \Delta P$).
- **Response**: `UsagePriceAnalysisResponse`

### `GET /api/v1/investigations/{id}/timeline`
Returns continuous 17-day spend timeline with rolling 7-day moving averages and DoD/WoW/MoM variance metrics.
- **Response**: `TimelineAnalysisResponse`

### `GET /api/v1/investigations/{id}/resources`
Returns resource inventory status, connected topology relationships, and hardware telemetry samples.
- **Response**: `ResourceInvestigationResponse`

### `GET /api/v1/investigations/{id}/correlations`
Returns cross-signal correlations across Waste Detections, Advisory Recommendations, and Active Alerts.
- **Response**: `CrossSignalCorrelationResponse`

### `GET /api/v1/investigations/{id}/root-causes`
Returns synthesized findings generated by the rule-based Hypothesis Evaluator.
- **Response**: `List[InvestigationFindingResponse]`

---

## 3. Collaboration & Findings Endpoints

### `POST /api/v1/investigations/{id}/notes`
Adds an analyst collaboration or diagnostic note.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Request Body**: `{"content": "Diagnostic findings from container logs..."}`
- **Response**: `InvestigationNoteResponse`

### `GET /api/v1/investigations/{id}/notes`
Retrieves all collaboration notes for the case in chronological order.
- **Response**: `List[InvestigationNoteResponse]`

### `POST /api/v1/investigations/{id}/findings`
Records an analyst-verified root cause or custom hypothesis.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Request Body**: `InvestigationFindingCreate`
- **Response**: `InvestigationFindingResponse`

### `GET /api/v1/investigations/{id}/findings`
Retrieves all structured findings (`FACT`, `CORRELATION`, `HYPOTHESIS`, `VERIFIED_CAUSE`).
- **Response**: `List[InvestigationFindingResponse]`

### `GET /api/v1/investigations/{id}/history`
Retrieves complete immutable lifecycle transition history with actor attribution.
- **Response**: `List[InvestigationHistoryResponse]`

### `GET /api/v1/investigations/{id}/evidence`
Retrieves immutable snapshots of linked billing records, resources, alerts, and waste detections.
- **Response**: `List[InvestigationEvidenceLinkResponse]`

---

## 4. Anomaly Direct Integration Endpoints

### `POST /api/v1/anomalies/{id}/investigate`
One-click endpoint to open or retrieve an investigation directly from an anomaly card.
- **Roles**: `FINOPS`, `ENGINEER`, `ADMIN`
- **Response**: `InvestigationCaseDetailResponse`

### `GET /api/v1/anomalies/{id}/investigation-summary`
Returns concise investigation status for embedding in anomaly lists and alert notifications.
- **Response**: `AnomalyInvestigationSummaryResponse`
