# CloudSage Production Observability & Telemetry

## 1. Overview

CloudSage implements enterprise telemetry designed for integration with Prometheus, Datadog, Grafana, OpenTelemetry, and centralized logging aggregators.

---

## 2. Health Probes

| Probe Endpoint | Purpose | Target Orchestrator | Expected Response |
| :--- | :--- | :--- | :--- |
| **`GET /health/liveness`** | Verifies process liveness; triggers container restart on hang. | Kubernetes / ECS Liveness Probe | `200 OK`<br/>`{"status":"healthy","service":"cloudsage-backend","version":"0.15.0"}` |
| **`GET /health/readiness`** | Verifies database connectivity before directing traffic. | Ingress / Service Load Balancer | `200 OK`<br/>`{"status":"ready","database":"healthy","version":"0.15.0"}` |
| **`GET /health/dependencies`** | Deep multi-tier component diagnostics and latency telemetry. | SRE Synthetics / Datadog Monitors | `200 OK`<br/>Detailed JSON breakdown across database, cache, and storage. |

### Sample `/health/dependencies` Output:
```json
{
  "status": "healthy",
  "timestamp": "2026-11-09T14:45:00.000Z",
  "total_latency_ms": 1.85,
  "dependencies": {
    "database": {
      "status": "healthy",
      "latency_ms": 1.25,
      "type": "relational_postgresql_compatible"
    },
    "cache_broker": {
      "status": "healthy",
      "mode": "redis",
      "latency_ms": 0.40
    },
    "storage": {
      "status": "healthy",
      "latency_ms": 0.20,
      "writable": true
    }
  }
}
```

---

## 3. Prometheus Metrics Instrumentation (`/metrics`)

CloudSage exposes Prometheus metrics in standard text exposition format on `GET /metrics`.

### Key Metric Vectors:

```promql
# Total incoming HTTP requests partitioned by method, endpoint, and status code
cloudsage_http_requests_total{method="GET",endpoint="/api/v1/recommendations",status_code="200"} 412.0

# HTTP request duration histogram across buckets (0.005s to 10.0s)
cloudsage_http_request_duration_seconds_bucket{endpoint="/api/v1/dashboard/overview",le="0.25"} 380.0

# Number of active in-flight requests currently being processed
cloudsage_active_requests 4.0

# FinOps domain: Total cost anomalies identified by severity and provider
cloudsage_finops_anomalies_detected_total{cloud_provider="AWS",severity="CRITICAL"} 14.0

# FinOps domain: Total identified potential monthly savings in USD
cloudsage_finops_potential_savings_usd{category="RESOURCE_RIGHTSIZING"} 45280.50

# FinOps domain: Total active recommendations in workspace
cloudsage_finops_recommendations_active{category="IDLE_RESOURCES"} 28.0
```

---

## 4. Request Correlation & Distributed Tracing

Every request is assigned or preserves an `X-Request-ID` header:
- Injected automatically via `RequestCorrelationMiddleware`.
- Added to response headers for client debugging.
- Bound to Python `ContextVar` for automatic inclusion in all structured logs emitted during the request lifecycle.

---

## 5. Structured JSON Logging

When `LOG_FORMAT=json`, the system serializes all application and access logs into standard JSON records:

```json
{
  "timestamp": "2026-11-09T14:45:10.123456Z",
  "level": "INFO",
  "logger": "cloudsage.access",
  "message": "GET /api/v1/recommendations 200 (14.2ms)",
  "request_id": "4b6890d2-9cb7-4f93-b6d8-11234abcd567",
  "duration_ms": 14.2,
  "status_code": 200,
  "client_ip": "10.0.4.12",
  "method": "GET",
  "path": "/api/v1/recommendations"
}
```

