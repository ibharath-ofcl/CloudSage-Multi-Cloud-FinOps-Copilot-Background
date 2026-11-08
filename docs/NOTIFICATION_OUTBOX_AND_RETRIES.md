# CloudSage Transactional Outbox & Retry Engine Guide

## 1. Overview

To guarantee reliable at-least-once notification delivery while keeping the core detection pipeline fully non-blocking, CloudSage implements the **Transactional Outbox Pattern**. Rather than invoking external HTTP endpoints or SMTP servers directly during rule evaluation, the system commits outbox records atomically within the database transaction. A separate asynchronous worker polls and dispatches these messages.

---

## 2. Transactional Outbox Model (`NotificationOutbox`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | Uuid | Primary key |
| `alert_instance_id` | Uuid | Foreign key to `alert_instances.id` |
| `channel` | String(32) | `IN_APP`, `EMAIL`, `WEBHOOK`, `SLACK`, `TEAMS` |
| `recipient` | String(256) | Destination address, webhook URL, or user ID |
| `subject` | String(256) | Notification title or email subject |
| `payload` | JSON | Structured JSON payload |
| `status` | String(32) | `PENDING`, `PROCESSING`, `DELIVERED`, `RETRYING`, `DEAD_LETTERED`, `CANCELLED` |
| `attempts` | Integer | Counter of executed dispatch attempts |
| `max_attempts` | Integer | Maximum retry limit (default `5`) |
| `next_attempt_at` | DateTime | Timestamp for the next scheduled retry |
| `last_attempt_at` | DateTime | Timestamp of the most recent dispatch attempt |
| `last_error` | Text | Captured error message from the last failure |
| `delivered_at` | DateTime | Timestamp when successfully delivered |

---

## 3. Exponential Backoff Algorithm

When an outbox item encounters a network error, HTTP 5xx error, or SMTP relay refusal:
1. `attempts` increments by 1.
2. If `attempts < max_attempts`, the status transitions to `RETRYING`.
3. The next attempt timestamp is scheduled using exponential backoff:
   $$\text{backoff\_seconds} = 2^{\text{attempts}} \times 60$$

| Attempt Number | Delay Before Retry | Cumulative Time Elapsed |
| :---: | :---: | :---: |
| 1 | 2 minutes (120s) | 2 minutes |
| 2 | 4 minutes (240s) | 6 minutes |
| 3 | 8 minutes (480s) | 14 minutes |
| 4 | 16 minutes (960s) | 30 minutes |
| 5 | **Escalated to DLQ** | Exceeded max retries |

---

## 4. Dead-Letter Queue (DLQ) & Operator Recovery

When an outbox record reaches `attempts >= max_attempts` (5 attempts) without success:
1. The status transitions to `DEAD_LETTERED`.
2. The item is removed from automatic polling schedules to prevent queue congestion.
3. It surfaces immediately on the **Delivery Status & DLQ Dashboard** (`frontend/src/pages/DeliveryStatusPanel.tsx`).

### Operator Recovery Actions:
- **Manual Retry**: An operator can click "Retry" in the UI or call `POST /api/v1/notification-deliveries/outbox/{id}/retry`. This resets `attempts = 0`, sets `status = PENDING`, and schedules immediate re-dispatch.
- **Cancellation**: An operator can click "Cancel" or call `POST /api/v1/notification-deliveries/outbox/{id}/cancel` to permanently abort delivery of obsolete notifications.

---

## 5. Latency & Delivery Attempts Ledger (`NotificationDeliveryAttempt`)

Every dispatch attempt records an immutable entry in `notification_delivery_attempts`:
- `outbox_id`: Linked outbox item.
- `attempt_number`: Attempt index (1, 2, 3...).
- `status`: `SUCCESS` or `FAILED`.
- `response_code`: HTTP status code (e.g. 200, 404, 502) or SMTP code.
- `response_body`: Truncated response body (first 500 characters).
- `latency_ms`: Execution duration measured via high-resolution timer (`time.perf_counter()`).
- `error_message`: Stack trace or exception message if an error occurred.
- `attempted_at`: UTC timestamp.

---

## 6. Pipeline Health & Telemetry API

`GET /api/v1/notification-deliveries/health`

### Response Schema:
```json
{
  "status": "HEALTHY",
  "pending_outbox_count": 0,
  "retrying_outbox_count": 1,
  "dead_lettered_count": 0,
  "delivery_attempts_24h": 48,
  "average_latency_ms": 142.5,
  "failure_rate_percentage": 2.08
}
```
If `dead_lettered_count > 5` or `failure_rate_percentage > 20%`, status automatically degrades to `DEGRADED`.
