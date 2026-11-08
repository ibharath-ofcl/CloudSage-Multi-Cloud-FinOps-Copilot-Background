# CloudSage Email & Webhook Delivery Integration Guide

## 1. Overview

CloudSage supports multi-channel notification dispatch across Email (SMTP / HTML templates) and Webhooks (custom HTTP, Slack incoming webhooks, Microsoft Teams connectors). All outbound messages are generated from standardized payload contracts and include explicit advisory notices to prevent unauthorized or automated destructive actions.

---

## 2. Mandatory Advisory Notice & Disclaimer

Every email template, webhook payload, and chat integration dispatched by CloudSage includes an explicit advisory disclaimer:

> **IMPORTANT NOTICE**: CloudSage is an advisory FinOps Copilot. All notifications, recommendations, and anomaly detections are strictly advisory. CloudSage will never autonomously alter, modify, terminate, or delete cloud infrastructure. All remediations must be reviewed and executed by authorized personnel following organizational change control policies.

---

## 3. Email Delivery Architecture (`EmailNotificationProvider`)

### 1. Configuration:
Configured via `backend/app/core/config.py`:
- `SMTP_HOST`: Hostname of the mail transfer agent (e.g. `smtp.sendgrid.net`).
- `SMTP_PORT`: SMTP port (default `587` with STARTTLS).
- `SMTP_USER` & `SMTP_PASSWORD`: SMTP credentials.
- `EMAIL_FROM`: Verified sender address (`alerts@cloudsage.com`).
- `NOTIFICATION_SAFE_LOCAL_MODE`: When enabled (default in testing/dev), emails are captured in an internal memory ring buffer without dialing external SMTP relays.

### 2. HTML Email Format:
The email template renders:
- High-contrast severity banner (`CRITICAL` in deep red, `HIGH` in amber).
- Financial metrics table: Actual Cost, Expected Cost, Excess Cost ($), and Spike Percentage (%).
- Attribution details: Cloud Provider, Account ID, Region, Service, and Timestamp.
- Root Cause Analysis summary and contributing resources.
- Direct CTA button linking to the alert in CloudSage (`/alerts/:id`).
- Standardized footer with the advisory disclaimer.

---

## 4. Custom Webhook Integration (`WebhookNotificationProvider`)

For integration with internal incident management tools (PagerDuty, OpsGenie, ServiceNow, custom microservices), the Webhook provider dispatches standard HTTP POST requests with a JSON body:

### Payload Schema:
```json
{
  "event_type": "COST_ANOMALY_ALERT",
  "version": "1.0",
  "timestamp": "2026-11-08T14:32:00Z",
  "alert_id": "792f615d-8861-41f3-9b8b-6822d69da8a8",
  "title": "AWS EC2 Compute Surge Alert",
  "severity": "CRITICAL",
  "provider": "AWS",
  "account_id": "111222333444",
  "service_name": "Amazon EC2",
  "region": "us-east-1",
  "financial_impact": {
    "actual_cost_usd": "780.5000",
    "expected_cost_usd": "250.0000",
    "excess_cost_usd": "530.5000",
    "deviation_percentage": "212.20"
  },
  "root_cause_analysis": {
    "summary": "Surge driven by c5.9xlarge on-demand instances launched in us-east-1a"
  },
  "action_url": "https://app.cloudsage.internal/alerts/792f615d-8861-41f3-9b8b-6822d69da8a8",
  "disclaimer": "CloudSage notifications are strictly advisory. Review and execute remediations via formal change management."
}
```

---

## 5. Slack Incoming Webhook Integration (`SlackNotificationProvider`)

CloudSage transforms anomaly alerts into Slack Block Kit structures:
- Rich colored sidebar attachments matching severity level.
- Multi-column metric fields displaying Actual Cost, Excess Cost, and Provider.
- Action blocks with interactive buttons to view the alert or acknowledge the ticket directly.

---

## 6. Microsoft Teams Connector (`TeamsNotificationProvider`)

CloudSage generates Microsoft Teams Adaptive Cards / MessageCard JSON:
- Activity title and subtitle displaying cloud attribution.
- Fact sets displaying financial impact, expected baseline, and detected date.
- OpenURI action linking back to the CloudSage workspace.

---

## 7. Webhook Security & SSRF Protection

All outbound webhook targets must pass rigorous server-side verification before request execution:
1. URL schema must be `http` or `https`.
2. Hostname is resolved via DNS and checked against RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), and cloud metadata (`169.254.169.254`).
3. HTTP request timeouts are enforced at 10 seconds.
