# CloudSage In-App Notification Center Guide

## 1. Overview

The CloudSage In-App Notification Center provides real-time alerting visibility directly within the web application. Designed for FinOps practitioners, platform engineers, and engineering managers, it combines an omnipresent header notification bell with an unread badge counter, a flyout popover for immediate triage, and a dedicated full-page Notification Center.

---

## 2. Notification Bell & Badge Counter

### Component Architecture:
- Implemented in `frontend/src/components/NotificationBell.tsx` and mounted in the global `Header.tsx`.
- Continuously polls `/api/v1/notifications/unread-count` at a configurable interval (30 seconds) with exponential backoff on network errors.
- Displays a pill badge with the exact unread count (e.g. `3` or `99+`). When count is zero, the badge cleanly disappears.

### Quick Actions Popover:
Clicking the bell toggles an accessible overlay containing:
- Recent unread notifications ordered chronologically.
- Severity pill badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- One-click navigation to the alert detail deep dive (`/alerts/:id`).
- Quick "Mark All Read" action button.
- Link to the full Notification Center (`/notifications`).

---

## 3. Dedicated Notification Center Page

The full-page Notification Center (`frontend/src/pages/NotificationCenter.tsx`) provides comprehensive notification lifecycle management:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Notifications & Alerts Center               [Mark All Read] [Refresh] │
│  Real-time multi-cloud cost anomaly notifications                      │
├────────────────────────────────────────────────────────────────────────┤
│  [All (14)]  [Unread (3)]  [Critical (2)]  [AWS]  [Azure]  [GCP]       │
├────────────────────────────────────────────────────────────────────────┤
│  🔍 Search notifications by title, service, account...                 │
├────────────────────────────────────────────────────────────────────────┤
│  🔴 CRITICAL  AWS EC2 Compute Surge ($780.50 actual vs $250.00 exp)    │
│     Account: 111222333444 | Region: us-east-1 | 12m ago • [Unread]    │
│     [View Alert Details] [Mark as Read]                                │
├────────────────────────────────────────────────────────────────────────┤
│  🟠 HIGH      Azure Blob Storage Spike ($1,500.00 vs $300.00 exp)      │
│     Subscription: sub-prod-east | Region: eastus | 1h ago • [Read]     │
│     [View Alert Details] [Mark as Unread]                              │
└────────────────────────────────────────────────────────────────────────┘
```

### Filtering & Organization:
1. **Tabs**: Filter by read state (`All`, `Unread Only`).
2. **Severity Badges**: Filter by severity level (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
3. **Provider Filters**: Filter by cloud platform (`AWS`, `Azure`, `GCP`).
4. **Text Search**: Real-time substring search against title, body, and service names.

---

## 4. Notification Data Model

The `InAppNotification` model persists user and role-targeted notifications:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | Uuid | Primary key |
| `alert_instance_id` | Uuid | Foreign key to `alert_instances.id` |
| `recipient_user_id` | String(128) | Target user email, user ID, role (`FINOPS_ENGINEER`), or `all` |
| `title` | String(256) | Notification headline |
| `message` | Text | Formatted summary of excess cost and deviation |
| `severity` | String(16) | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `is_read` | Boolean | Read state |
| `read_at` | DateTime | Timestamp when marked read |
| `created_at` | DateTime | Creation timestamp |

---

## 5. REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/notifications` | List in-app notifications for authenticated user |
| `GET` | `/api/v1/notifications/unread-count` | Retrieve badge counter for current user |
| `POST` | `/api/v1/notifications/{id}/read` | Mark individual notification as read |
| `POST` | `/api/v1/notifications/{id}/unread` | Mark individual notification as unread |
| `POST` | `/api/v1/notifications/mark-all-read` | Mark all pending notifications as read |
