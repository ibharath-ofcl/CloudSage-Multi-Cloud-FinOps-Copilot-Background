# Resource Telemetry Analytics & Visualization

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Overview

Cloud cost recommendations (such as compute rightsizing or idle instance termination) are inherently risky if engineering teams lack empirical evidence of actual resource utilization. A rightsizing suggestion that halves CPU allocation without inspecting peak utilization risks triggering production performance degradations.

Stage 11 introduces the **Resource Telemetry Analytics & Visualization** subsystem. This capability extracts, normalizes, aggregates, and visualizes time-series operational metrics directly alongside financial recommendations and waste findings.

### Core Principles:

1. **Non-Fabrication Guarantee:** CloudSage strictly forbids generating synthetic or mock telemetry data in production API responses. If an asset has no collected metrics, the system returns an explicit empty state (`has_telemetry: False`) with actionable guidance.
2. **Multi-Metric Support:** Captures and aggregates CPU Utilization (%), Memory Utilization (%), Network In/Out (Bytes/sec or Mbps), and Disk Read/Write IOPS.
3. **Statistical Aggregation:** Computes `min`, `max`, `avg`, and `latest` values across customizable observation windows (7, 14, 30, or 90 days).
4. **Interactive Visualization:** Renders interactive, lightweight SVG charts in the frontend with zero heavy charting dependencies, providing smooth tooltips, trendlines, and threshold markers.

---

## 2. Telemetry Architecture & Data Model

The telemetry pipeline queries historical metric samples stored in the `resource_metrics` table (established in Stage 5) and aggregates them on demand:

```
┌────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                  │
│                     resource_metrics                   │
│   (resource_id, timestamp, metric_name, metric_value)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              TelemetryService (Backend)                │
│  - Filters by resource_id and date window (e.g. 14d)   │
│  - Computes min, max, avg, latest, sample_count        │
│  - Normalizes timestamps to ISO-8601 strings           │
│  - Enforces explicit empty state if no samples found   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   REST API Endpoints                   │
│  - GET /api/v1/inventory/resources/{id}/telemetry      │
│  - GET /api/v1/recommendations/{id}/telemetry          │
│  - GET /api/v1/waste/findings/{id}/telemetry           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                 TelemetryPanel (React)                 │
│  - Metric Selector (CPU, Memory, Network, Disk)        │
│  - Window Selector (7d, 14d, 30d, 90d)                 │
│  - KPI Badges (Min, Max, Avg, Latest)                  │
│  - Interactive SVG Area/Line Chart                     │
│  - Empty State Notice with Monitoring Instructions     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Statistical Aggregations & Math

For each supported metric $m \in \{\text{cpu\_utilization}, \text{memory\_utilization}, \text{network\_in}, \text{network\_out}, \text{disk\_iops}\}$ over an observation window $W$ consisting of $N$ recorded data points $(t_i, v_i)$:

- **Minimum:**  
  $$\min(v) = \min_{i=1 \dots N} v_i$$
- **Maximum:**  
  $$\max(v) = \max_{i=1 \dots N} v_i$$
- **Average:**  
  $$\text{avg}(v) = \frac{1}{N} \sum_{i=1}^N v_i$$
- **Latest:**  
  $$v_{\text{latest}} = v_N \quad \text{where } t_N = \max_{i=1 \dots N} t_i$$

All aggregations are rounded to two decimal places for human readability and charted chronologically.

---

## 4. API Response Schema

```json
{
  "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-0abcdef1234567890",
  "observation_window_days": 14,
  "start_time": "2026-10-25T11:00:00Z",
  "end_time": "2026-11-08T11:00:00Z",
  "has_telemetry": true,
  "metrics": {
    "cpu_utilization": {
      "metric_name": "cpu_utilization",
      "unit": "%",
      "min": 1.25,
      "max": 14.80,
      "avg": 4.12,
      "latest": 3.40,
      "sample_count": 336,
      "time_series": [
        {"timestamp": "2026-10-25T12:00:00Z", "value": 3.80},
        {"timestamp": "2026-10-25T13:00:00Z", "value": 4.10}
      ]
    }
  }
}
```

### Unmonitored Asset Schema (Explicit Empty State):

```json
{
  "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-unmonitored",
  "observation_window_days": 14,
  "start_time": "2026-10-25T11:00:00Z",
  "end_time": "2026-11-08T11:00:00Z",
  "has_telemetry": false,
  "metrics": {},
  "notice": "No telemetry metrics collected for this resource in the specified observation window. Enable CloudWatch / Azure Monitor / Google Cloud Monitoring agents to collect utilization time-series."
}
```

---

## 5. UI Visualization Component (`TelemetryPanel.tsx`)

The React component provides:
1. **Metric Tabs:** Toggle effortlessly between CPU, Memory, Network In/Out, and Disk IOPS.
2. **Window Selector:** Choose between 7, 14, 30, and 90-day timeframes.
3. **KPI Stat Badges:** Instant visual display of Min, Max, Average, and Latest values.
4. **SVG Time-Series Chart:** Custom SVG rendering with gradient fills, gridlines, axis labels, and hover tooltips showing exact timestamps and values.
5. **Zero Data Warning:** Non-destructive warning screen informing operators that monitoring data is unavailable, preventing blind rightsizing decisions.
