# CloudSage Multi-Cloud Waste Detection REST API Reference

The Waste Detection REST API exposes 13 endpoints providing complete control over detection runs, finding queries, review workflows, and financial summaries.

All endpoints are registered under `/api/v1/waste-detection`.

---

## 1. API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/waste-detection/run` | Trigger a waste detection run across inventoried resources. |
| `GET` | `/api/v1/waste-detection/findings` | List findings with multi-dimensional filtering and pagination. |
| `GET` | `/api/v1/waste-detection/findings/{finding_id}` | Retrieve details for a single waste finding. |
| `GET` | `/api/v1/waste-detection/summary` | Executive KPI summary of open findings and potential savings. |
| `GET` | `/api/v1/waste-detection/categories` | Breakdown of waste findings and savings by category. |
| `GET` | `/api/v1/waste-detection/by-provider` | Breakdown of waste findings and savings by cloud provider. |
| `GET` | `/api/v1/waste-detection/by-account` | Breakdown of waste findings by account / project. |
| `GET` | `/api/v1/waste-detection/runs` | List historical detection runs with execution statistics. |
| `GET` | `/api/v1/waste-detection/runs/{run_id}` | Detailed execution record for a specific detection run. |
| `GET` | `/api/v1/waste-detection/savings-summary` | Detailed financial intelligence and top savings opportunities. |
| `GET` | `/api/v1/waste-detection/detectors` | Catalog of registered detectors and default thresholds. |
| `PATCH` | `/api/v1/waste-detection/findings/{finding_id}/status` | Human review: Acknowledge, Dismiss, Resolve, or Snooze. |
| `GET` | `/api/v1/waste-detection/findings/{finding_id}/evidence` | Complete telemetry proof and observation evidence. |

---

## 2. Selected Endpoint Specifications

### 2.1 Trigger Detection Run
- **`POST /api/v1/waste-detection/run`**
- **Request Body**:
  ```json
  {
    "provider": "AWS",
    "account_id": "112233445566",
    "lookback_days": 7
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "run_id": "9a16db99-c68f-4620-be2b-01f2ab34fe11",
    "provider": "AWS",
    "status": "COMPLETED",
    "total_resources_evaluated": 120,
    "findings_created": 8,
    "findings_updated": 4,
    "findings_unchanged": 12,
    "total_estimated_monthly_savings": "1250.0000",
    "started_at": "2026-11-07T14:00:00Z",
    "completed_at": "2026-11-07T14:00:05Z"
  }
  ```

### 2.2 List Findings
- **`GET /api/v1/waste-detection/findings?provider=AWS&severity=HIGH&limit=20`**
- **Query Parameters**:
  - `provider`: Filter by AWS, AZURE, GCP.
  - `account_id`: Filter by cloud account.
  - `waste_type`: Filter by waste category enum.
  - `severity`: Filter by `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`.
  - `status`: Filter by `ACTIVE`, `OPEN`, `ACKNOWLEDGED`, `SNOOZED`, `DISMISSED`, `RESOLVED`.
  - `min_savings`: Decimal threshold for minimum monthly savings.
  - `limit`, `offset`: Pagination controls.

### 2.3 Update Finding Status (Human-in-the-Loop)
- **`PATCH /api/v1/waste-detection/findings/{finding_id}/status`**
- **Request Body**:
  ```json
  {
    "status": "DISMISSED",
    "reason": "Instance is a standby failover node for disaster recovery",
    "user": "finops-engineer@company.com"
  }
  ```
- **Response** (`200 OK`): Returns updated `WasteFindingResponse`.

### 2.4 Telemetry Proof Inspection
- **`GET /api/v1/waste-detection/findings/{finding_id}/evidence`**
- **Response** (`200 OK`):
  ```json
  {
    "finding_id": "...",
    "resource_id": "i-0123456789abcdef0",
    "provider": "AWS",
    "waste_type": "IDLE_COMPUTE",
    "confidence_score": "0.8500",
    "observation_window_days": 7,
    "telemetry_proof": {
      "avg_cpu_utilization_pct": 2.1,
      "peak_cpu_utilization_pct": 4.5,
      "avg_network_io_mb_day": 1.2
    }
  }
  ```
