# CloudSage Escalation Policies & Notification Preferences Guide

## 1. Overview

Different stakeholders within an enterprise require different alerting cadences and communication channels. CloudSage provides a dual-tier preference model:
1. **Rule-Level Escalation Policies**: System-wide escalation rules configured on alert definitions.
2. **User-Level Notification Preferences**: Individual user profiles defining active channels, minimum severity, quiet hours, and digest frequencies.

---

## 2. Rule-Level Escalation Policies

Configured on `AlertRule.escalation_policy` (JSON):
- **Unacknowledged Escalation**: If an alert remains in `OPEN` status for more than $N$ hours (default 4 hours), the system escalates the alert to secondary on-call distribution lists.
- **Severity Escalation**: If an ongoing anomaly's excess cost expands by $\ge 50\%$ or transitions from `HIGH` to `CRITICAL`, cooldown windows are bypassed and an immediate high-priority alert is dispatched.
- **Escalation Levels**: Tracked via `AlertInstance.escalation_level` (0 = baseline, 1 = first escalation, 2 = manager escalation).

---

## 3. User-Level Notification Preferences (`NotificationPreference`)

Every user can configure their personal notification preferences via `frontend/src/pages/NotificationPreferencesPage.tsx` or `PUT /api/v1/notification-preferences/me`:

| Preference Attribute | Description | Default |
| :--- | :--- | :--- |
| `enabled_channels` | List of channels user wishes to receive: `IN_APP`, `EMAIL`, `SLACK`, `TEAMS` | `["IN_APP", "EMAIL"]` |
| `min_severity` | Minimum severity required to notify this user: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | `MEDIUM` |
| `quiet_hours_enabled` | Whether non-critical alerts are suppressed during off-hours | `False` |
| `quiet_hours_start_utc` | Start of quiet hours in UTC (e.g. `22:00`) | `22:00` |
| `quiet_hours_end_utc` | End of quiet hours in UTC (e.g. `08:00`) | `08:00` |
| `receive_digests` | Whether to receive consolidated anomaly rollups | `True` |
| `digest_frequency` | Digest cadence: `DAILY`, `WEEKLY`, `NONE` | `DAILY` |

---

## 4. Quiet Hours & Non-Critical Suppression

When quiet hours are enabled for a user:
- The system checks `current_utc_time` against `[quiet_hours_start_utc, quiet_hours_end_utc]`.
- If the current time falls within the window:
  - **`CRITICAL` Alerts**: Always bypass quiet hours and are delivered immediately.
  - **`HIGH`, `MEDIUM`, `LOW` Alerts**: Direct outbound notifications (Email, Slack, Webhook) are suppressed or deferred to the daily morning digest. In-app notifications remain visible in the Notification Center for the user's next login.

---

## 5. Daily and Weekly Digests

To eliminate email fatigue for management and engineering teams:
- The background task `execute_daily_digest_job` runs every morning at 08:00 UTC.
- It aggregates all anomalies, materialized alerts, and resolved incidents from the preceding 24 hours (or 7 days for weekly subscribers).
- It dispatches a consolidated HTML summary report with spending totals, top contributing services, and active investigation status.
