# Cost Anomaly Detection REST API Reference

## 1. Overview

The CloudSage Cost Anomaly Detection Engine exposes 14 REST endpoints under prefix `/api/v1/anomaly-detection`. All operations are strictly advisory and non-destructive.

---

## 2. Endpoints Summary Table

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **`POST`** | `/api/v1/anomaly-detection/run` | Triggers a multi-cloud cost anomaly detection scan. |
| **`GET`** | `/api/v1/anomaly-detection/anomalies` | Lists anomalies with multi-faceted filtering and pagination. |
| **`GET`** | `/api/v1/anomaly-detection/anomalies/{anomaly_id}` | Retrieves full details for a specific cost anomaly finding. |
| **`GET`** | `/api/v1/anomaly-detection/summary` | Executive and operational financial summary of open anomalies. |
| **`GET`** | `/api/v1/anomaly-detection/baselines` | Lists computed statistical expenditure baselines. |
| **`GET`** | `/api/v1/anomaly-detection/baselines/{baseline_id}` | Retrieves details of a specific statistical baseline. |
| **`GET`** | `/api/v1/anomaly-detection/trends/{anomaly_id}` | Contiguous daily time-series surrounding an anomaly for charting. |
| **`GET`** | `/api/v1/anomaly-detection/contributors/{anomaly_id}` | Ranked contributing resources and SKUs driving the anomaly. |
| **`GET`** | `/api/v1/anomaly-detection/evidence/{anomaly_id}` | Detailed statistical parameters and source billing references. |
| **`GET`** | `/api/v1/anomaly-detection/runs` | Lists historical execution audit logs. |
| **`GET`** | `/api/v1/anomaly-detection/runs/{run_id}` | Retrieves execution statistics for a specific detection run. |
| **`GET`** | `/api/v1/anomaly-detection/methods` | Lists registered anomaly detection algorithms and formulas. |
| **`GET`** | `/api/v1/anomaly-detection/financial-impact` | Deduplicated financial impact and annualized projections. |
| **`PATCH`**| `/api/v1/anomaly-detection/anomalies/{anomaly_id}/status` | Updates review status (ACKNOWLEDGE, INVESTIGATE, DISMISS, RESOLVE). |

---

## 3. Detailed Endpoint Specifications

### 1. Trigger Detection Run
- **URL**: `POST /api/v1/anomaly-detection/run`
- **Request Body**:
```json
{
  "provider": "ALL",
  "account_id": null,
  "service_name": null,
  "baseline_window_days": 30
}
```
- **Response** (`200 OK`):
```json
{
  "run_id": "7a35606e-821f-4b07-9b2f-b4df499c755c",
  "provider": "ALL",
  "scope": "FULL",
  "status": "COMPLETED",
  "total_series_evaluated": 12,
  "baselines_generated": 12,
  "anomalies_created": 3,
  "anomalies_updated": 0,
  "anomalies_unchanged": 0,
  "anomalies_resolved": 0,
  "total_excess_cost": "1840.0000",
  "detector_summary": {
    "statistical_ensemble_detector": 2,
    "change_point_detector": 1
  },
  "error_details": [],
  "started_at": "2026-11-07T12:00:00Z",
  "completed_at": "2026-11-07T12:00:02Z"
}
```

---

### 2. List Anomalies
- **URL**: `GET /api/v1/anomaly-detection/anomalies`
- **Query Parameters**:
  - `provider`: `AWS`, `AZURE`, `GCP`
  - `status`: `DETECTED`, `INVESTIGATING`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`, `REOPENED`
  - `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
  - `category`: `SERVICE_SPIKE`, `RESOURCE_SPIKE`, `PERSISTENT_STEP`, `NEW_SPEND`
  - `limit`: Default `50` (1 to 500)
  - `offset`: Default `0`
- **Response** (`200 OK`):
```json
{
  "total": 1,
  "items": [
    {
      "id": "68d70009-f20d-4146-90e0-d897e4077650",
      "detector_id": "service_cost_spike_detector",
      "detector_version": "1.0.0",
      "provider": "AWS",
      "account_id": "111122223333",
      "service_category": "DATABASE",
      "service_name": "AmazonDynamoDB",
      "region": "us-east-1",
      "resource_id": "arn:aws:dynamodb:us-east-1:111122223333:table/Orders",
      "anomaly_category": "SERVICE_SPIKE",
      "title": "Spike on AmazonDynamoDB",
      "explanation": "Sudden surge in provisioned throughput.",
      "anomaly_date": "2026-10-15",
      "detection_method": "Z_SCORE",
      "actual_cost": "750.0000",
      "expected_cost": "150.0000",
      "absolute_deviation": "600.0000",
      "spike_percentage": "400.0000",
      "z_score": "4.5000",
      "estimated_excess_cost": "600.0000",
      "projected_monthly_impact": "600.0000",
      "currency": "USD",
      "severity": "HIGH",
      "status": "DETECTED",
      "confidence_score": "0.9500",
      "baseline_window_days": 30,
      "observation_window_days": 1
    }
  ],
  "limit": 50,
  "offset": 0
}
```

---

### 3. Update Anomaly Status
- **URL**: `PATCH /api/v1/anomaly-detection/anomalies/{anomaly_id}/status`
- **Request Body**:
```json
{
  "status": "DISMISSED",
  "user": "lead_architect@company.com",
  "reason": "Expected performance load test during staging rollout.",
  "investigation_notes": "Load test verified with platform engineering team."
}
```
- **Response** (`200 OK`):
Returns the updated `CostAnomalyResponse` object with `status: "DISMISSED"`.
