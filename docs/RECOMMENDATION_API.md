# CloudSage Advisory Recommendation REST API Reference

## 1. API Architecture Overview

The Recommendation REST API is exposed under `/api/v1/recommendations` and provides 16 enterprise endpoints supporting run triggers, filtering, summaries, audit logs, lifecycle transitions, and data export.

Base Path: `/api/v1/recommendations`

---

## 2. Endpoint Catalog

| Method | Path | Summary | Response Model / Status |
| :--- | :--- | :--- | :--- |
| `POST` | `/run` | Trigger recommendation generation run across cloud resources. | `RecommendationRunResponse` (201) |
| `GET` | `/` | List recommendations with rich query filtering and pagination. | `List[RecommendationResponse]` (200) |
| `GET` | `/summary` | Executive multi-cloud KPI summary across all recommendations. | `RecommendationSummaryResponse` (200) |
| `GET` | `/priorities` | Breakdown of recommendations grouped by priority tiers (P1-P4). | `List[RecommendationPriorityBreakdown]` (200) |
| `GET` | `/categories` | Breakdown of recommendations grouped by action category. | `List[RecommendationCategoryBreakdown]` (200) |
| `GET` | `/runs` | List historical recommendation generation execution runs. | `List[RecommendationRunResponse]` (200) |
| `GET` | `/runs/{run_id}` | Detailed execution metrics for a specific recommendation run. | `RecommendationRunResponse` (200) |
| `GET` | `/financial-impact` | Realized vs unrealized savings and realization rates. | `FinancialImpactResponse` (200) |
| `GET` | `/owners` | Recommendations and savings aggregated by resource owner tag. | `List[OwnerImpactResponse]` (200) |
| `GET` | `/export` | Export recommendations as JSON or CSV file download. | `text/csv` or `application/json` (200) |
| `GET` | `/{id}` | Detailed recommendation payload with guidance and assumptions. | `RecommendationDetailResponse` (200) |
| `GET` | `/{id}/evidence` | Supporting telemetry, metric series, waste, and anomaly links. | `List[RecommendationEvidenceResponse]` (200) |
| `GET` | `/{id}/history` | Complete lifecycle transition and actor action audit trail. | `List[RecommendationHistoryResponse]` (200) |
| `GET` | `/{id}/savings` | Detailed financial breakdown, current/projected costs, and ROI. | `RecommendationSavingsDetail` (200) |
| `PATCH`| `/{id}/status` | Execute lifecycle state transition (review, approve, reject). | `RecommendationResponse` (200) |
| `POST` | `/{id}/feedback`| Submit engineer feedback, rating, or implementation notes. | `RecommendationHistoryResponse` (200) |

---

## 3. Key Endpoint Payloads

### A. Trigger Recommendation Run
`POST /api/v1/recommendations/run`
```json
{
  "provider": "AWS",
  "strategies": ["idle_compute_strategy", "compute_rightsizing_strategy"],
  "account_id": "112233445566",
  "scope": "FULL"
}
```

Response (`201 Created`):
```json
{
  "run_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "provider": "AWS",
  "scope": "FULL",
  "status": "COMPLETED",
  "total_evaluated": 15,
  "recommendations_created": 4,
  "recommendations_updated": 2,
  "recommendations_unchanged": 0,
  "recommendations_suppressed": 1,
  "total_monthly_savings": "1250.0000",
  "total_annual_savings": "15000.0000",
  "strategy_summary": {
    "idle_compute_strategy": 3,
    "compute_rightsizing_strategy": 3
  },
  "error_details": [],
  "started_at": "2026-11-07T12:00:00Z",
  "completed_at": "2026-11-07T12:00:02Z"
}
```

### B. Lifecycle State Transition
`PATCH /api/v1/recommendations/{id}/status`
```json
{
  "status": "APPROVED",
  "actor_email": "finops-lead@enterprise.com",
  "notes": "Approved for execution in upcoming sprint maintenance window."
}
```

### C. Rejection with Mandatory Reason
`PATCH /api/v1/recommendations/{id}/status`
```json
{
  "status": "DISMISSED",
  "actor_email": "architect@enterprise.com",
  "reason": "Instance is required for annual disaster recovery drill next month."
}
```
*(If `reason` is omitted, returns HTTP `422 Unprocessable Entity`).*
