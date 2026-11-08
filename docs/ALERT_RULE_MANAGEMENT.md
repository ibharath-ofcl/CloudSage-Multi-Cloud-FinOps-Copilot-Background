# CloudSage Alert Rule Management Guide

## 1. Overview

The CloudSage Alert Rule Management subsystem enables FinOps administrators and engineering leaders to define, simulate, update, and manage targeted alert rules. Alert rules specify the dimensional scope, financial trigger thresholds, delivery channels, recipients, and cooldown parameters for cost anomalies across AWS, Azure, and GCP.

---

## 2. Rule Model & Multi-Dimensional Scoping

Alert rules (`AlertRule` model) support granular multi-dimensional filtering to ensure notifications reach the appropriate teams without alert fatigue:

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | String(128) | Human-readable rule title (e.g., "Prod AWS EC2 Compute Surge") |
| `description` | Text | Operational context and alert rationale |
| `provider` | String(16) | Target hyperscaler: `AWS`, `AZURE`, `GCP`, or `ALL` |
| `account_id` | String(64) | Specific cloud account, subscription ID, or GCP project ID (optional) |
| `region` | String(64) | Specific cloud region (e.g. `us-east-1`, `westeurope`, `us-central1`) (optional) |
| `service_name` | String(128) | Service identifier (e.g., `Amazon EC2`, `Virtual Machines`, `BigQuery`) (optional) |
| `environment` | String(64) | Environment tag filter (e.g., `production`, `staging`, `development`) |
| `owner` | String(128) | Team or individual owner tag scope |
| `cost_center` | String(64) | Financial cost center identifier scope |
| `min_severity` | String(16) | Minimum severity to trigger: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `min_excess_cost` | Numeric(18, 4) | Minimum unexpected dollar excess required (e.g., `$100.0000`) |
| `percentage_deviation_threshold` | Numeric(8, 2) | Minimum percentage increase above baseline (e.g., `25.00%`) |
| `channels` | JSON | Active delivery channels: `IN_APP`, `EMAIL`, `WEBHOOK`, `SLACK`, `TEAMS` |
| `recipients` | JSON | Target email addresses, webhook endpoints, or Slack channels |
| `cooldown_minutes` | Integer | Minimum suppression interval between repeated alerts (default 1440 min / 24h) |
| `escalation_policy` | JSON | Escalation criteria (e.g. bypass cooldown on `CRITICAL` surge) |
| `is_enabled` | Boolean | Whether rule actively evaluates incoming anomalies |
| `is_archived` | Boolean | Soft-deletion flag |

---

## 3. Dry-Run Rule Evaluation & Preview API

Before deploying a rule to production, operators can simulate its behavior against historical anomalies using the Dry-Run Preview endpoint:

`POST /api/v1/alert-rules/preview`

### Sample Request:
```json
{
  "provider": "AWS",
  "min_severity": "HIGH",
  "min_excess_cost": 250.0,
  "percentage_deviation_threshold": 30.0
}
```

### Sample Response:
```json
{
  "matched_count": 4,
  "estimated_alert_frequency_30d": 4,
  "sample_matches": [
    {
      "anomaly_id": "c949259e-c14f-4a21-8911-5da283f43800",
      "provider": "AWS",
      "service_name": "Amazon EC2",
      "region": "us-east-1",
      "severity": "HIGH",
      "actual_cost": "780.5000",
      "expected_cost": "250.0000",
      "estimated_excess_cost": "530.5000",
      "spike_percentage": "212.20",
      "detected_at": "2026-11-08T10:15:00Z"
    }
  ]
}
```

The dry-run preview inspects the last 100 detected cost anomalies, counts matching events, and surfaces a sample list of affected services, allowing operators to verify threshold sensitivity without generating alerts or outbox messages.

---

## 4. Rule REST API Endpoints

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/alert-rules` | List alert rules with multi-dimensional filtering | Any Authenticated |
| `POST` | `/api/v1/alert-rules` | Create new alert rule with SSRF validation | ADMIN / FINOPS_ADMIN |
| `GET` | `/api/v1/alert-rules/{rule_id}` | Retrieve rule configuration by ID | Any Authenticated |
| `PUT` | `/api/v1/alert-rules/{rule_id}` | Update existing rule attributes | ADMIN / FINOPS_ADMIN |
| `POST` | `/api/v1/alert-rules/{rule_id}/toggle` | Toggle rule enabled/disabled status | ADMIN / FINOPS_ADMIN |
| `DELETE` | `/api/v1/alert-rules/{rule_id}` | Soft delete rule (sets `is_archived=True`) | ADMIN / FINOPS_ADMIN |
| `POST` | `/api/v1/alert-rules/preview` | Dry-run preview matching simulation | Any Authenticated |

---

## 5. Security & SSRF Validation

When alert rules are created or updated with webhook recipients (`http://` or `https://`), the endpoint enforces server-side SSRF validation (`validate_webhook_url`). Any recipient resolving to private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopbacks (`127.0.0.1`), or cloud provider metadata IPs (`169.254.169.254`) is immediately rejected with HTTP 400 Bad Request.
