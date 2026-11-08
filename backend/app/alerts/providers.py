"""
CloudSage Multi-Channel Notification Providers.
Implements modular delivery adapters for In-App Notification Center,
SMTP/Email (with safe local development mode), and Webhooks (with SSRF defense).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from backend.app.core.config import settings
from backend.app.alerts.security import validate_webhook_url


class BaseNotificationProvider(ABC):
    """Abstract interface implemented by all outbound notification adapters."""

    @abstractmethod
    def dispatch(
        self,
        recipient: str,
        subject: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, int, str, str]:
        """
        Dispatches a notification to the specified recipient.
        Returns: (success: bool, response_code: int, response_body: str, error_message: str)
        """
        pass


class InAppNotificationProvider(BaseNotificationProvider):
    """Dispatches in-app notification records into the database center."""

    def dispatch(
        self,
        recipient: str,
        subject: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, int, str, str]:
        # In-app records are maintained directly in the DB
        return True, 200, "Persisted in In-App Notification Center", ""


class EmailNotificationProvider(BaseNotificationProvider):
    """
    Renders enterprise HTML & plain-text alert emails with financial summaries
    and advisory-only guardrails. Supports safe local development capture.
    """
    captured_emails: List[Dict[str, Any]] = []

    def __init__(self, safe_mode: Optional[bool] = None):
        self.safe_mode = settings.NOTIFICATION_SAFE_LOCAL_MODE if safe_mode is None else safe_mode

    @classmethod
    def clear_captured_emails(cls):
        cls.captured_emails.clear()

    def render_email_html(self, subject: str, payload: Dict[str, Any]) -> str:
        """Renders responsive HTML template with FinOps color coding and evidence summary."""
        title = payload.get("title", subject)
        severity = payload.get("severity", "MEDIUM")
        provider = payload.get("provider", "UNKNOWN")
        account_id = payload.get("account_id", "N/A")
        service_name = payload.get("service_name", "Unknown Service")
        current_cost = payload.get("current_cost", "0.00")
        expected_cost = payload.get("expected_cost", "0.00")
        excess_cost = payload.get("excess_cost", "0.00")
        pct_dev = payload.get("percentage_deviation", "0.00")
        alert_id = payload.get("alert_instance_id", "")
        explanation = payload.get("explanation", "Cost anomaly detected by CloudSage statistical engine.")

        # Severity banner color
        sev_color = {
            "CRITICAL": "#ef4444",
            "HIGH": "#f97316",
            "MEDIUM": "#eab308",
            "LOW": "#3b82f6",
        }.get(severity, "#64748b")

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: #0f172a; padding: 20px 24px; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 18px; font-weight: 700; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 700; color: #ffffff; background-color: {sev_color}; margin-top: 8px; }}
    .content {{ padding: 24px; }}
    .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 20px 0; }}
    .metric-card {{ background: #f1f5f9; padding: 12px; border-radius: 6px; }}
    .metric-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; }}
    .metric-val {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
    .excess {{ color: #dc2626; }}
    .btn {{ display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 14px; margin-top: 16px; }}
    .footer {{ background: #f8fafc; padding: 16px 24px; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>CloudSage FinOps Alert</h1>
      <span class="badge">{severity} SEVERITY</span>
    </div>
    <div class="content">
      <h2 style="font-size: 16px; margin: 0 0 12px 0;">{title}</h2>
      <p style="font-size: 13px; color: #475569; margin: 0 0 16px 0;">{explanation}</p>
      
      <div style="font-size: 12px; color: #334155; margin-bottom: 12px;">
        <strong>Cloud Provider:</strong> {provider} | <strong>Account:</strong> {account_id} | <strong>Service:</strong> {service_name}
      </div>

      <table width="100%" style="border-collapse: collapse; margin: 16px 0;">
        <tr>
          <td style="background: #f1f5f9; padding: 12px; border-radius: 6px; width: 48%;">
            <div style="font-size: 11px; color: #64748b; font-weight: 600;">OBSERVED COST</div>
            <div style="font-size: 18px; font-weight: 700; color: #0f172a;">${current_cost} USD</div>
          </td>
          <td style="width: 4%;"></td>
          <td style="background: #fee2e2; padding: 12px; border-radius: 6px; width: 48%;">
            <div style="font-size: 11px; color: #991b1b; font-weight: 600;">UNBUDGETED EXCESS</div>
            <div style="font-size: 18px; font-weight: 700; color: #dc2626;">+${excess_cost} USD (+{pct_dev}%)</div>
          </td>
        </tr>
      </table>

      <a href="http://localhost:5173/alerts/{alert_id}" class="btn">Investigate Anomaly in Workspace</a>
    </div>
    <div class="footer">
      <strong>STRICT ADVISORY NOTICE:</strong> CloudSage is an advisory FinOps copilot. No cloud modifications, deletions, or mutations are performed autonomously. All remedial actions require human authorization.<br>
      CloudSage Multi-Cloud FinOps Platform | <a href="http://localhost:5173/preferences" style="color: #64748b;">Manage Notification Preferences</a>
    </div>
  </div>
</body>
</html>"""
        return html

    def dispatch(
        self,
        recipient: str,
        subject: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, int, str, str]:
        html_body = self.render_email_html(subject, payload)

        if self.safe_mode:
            # Safe local mode: capture email in memory for testing/verification without SMTP failure
            record = {
                "recipient": recipient,
                "subject": subject,
                "payload": payload,
                "html_length": len(html_body),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.captured_emails.append(record)
            return True, 250, f"Email safely recorded in local dev mode for {recipient}", ""

        # Live SMTP delivery
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = recipient

            text_part = MIMEText(f"{subject}\n\n{payload.get('explanation', '')}\nExcess: ${payload.get('excess_cost', '0.00')} USD\n\nAdvisory Notice: CloudSage does not mutate cloud infrastructure autonomously.", "plain")
            html_part = MIMEText(html_body, "html")
            msg.attach(text_part)
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            return True, 250, f"Email delivered successfully to {recipient}", ""
        except Exception as e:
            return False, 500, "", f"SMTP delivery failed: {str(e)}"


class WebhookNotificationProvider(BaseNotificationProvider):
    """
    Dispatches structured JSON notifications to authorized external webhooks.
    Applies strict SSRF destination validation against internal/metadata IPs.
    """
    captured_webhooks: List[Dict[str, Any]] = []

    def __init__(self, allow_test_destinations: bool = False):
        self.allow_test_destinations = allow_test_destinations

    @classmethod
    def clear_captured_webhooks(cls):
        cls.captured_webhooks.clear()

    def dispatch(
        self,
        recipient: str,
        subject: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, int, str, str]:
        # 1. Test destination check (e.g. test://, mock://, or allow_test_destinations)
        if recipient.startswith("test://") or recipient.startswith("mock://") or (self.allow_test_destinations and "test" in recipient):
            self.captured_webhooks.append({
                "recipient": recipient,
                "subject": subject,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return True, 200, json.dumps({"status": "received", "event_id": payload.get("alert_instance_id")}), ""

        # 2. SSRF Validation
        try:
            validate_webhook_url(recipient, allow_private_for_test=self.allow_test_destinations)
        except Exception as ssrf_err:
            return False, 400, "", f"SSRF Validation Blocked: {str(ssrf_err)}"

        # 3. Live HTTP dispatch
        try:
            req_data = json.dumps({
                "event": "cost_anomaly_alert",
                "subject": subject,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": payload,
            }).encode("utf-8")

            req = urllib.request.Request(
                recipient,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "CloudSage-Alerting-Hub/1.0",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as response:
                status_code = response.getcode()
                resp_text = response.read().decode("utf-8")[:500]
                if 200 <= status_code < 300:
                    return True, status_code, resp_text, ""
                return False, status_code, resp_text, f"HTTP Error {status_code}"

        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8")[:500] if he.fp else ""
            return False, he.code, err_body, f"HTTP error {he.code}"
        except Exception as exc:
            return False, 502, "", f"Webhook dispatch connection error: {str(exc)}"


class SlackNotificationProvider(BaseNotificationProvider):
    """Formats and dispatches Slack Block Kit cards to Slack incoming webhook URLs."""

    def __init__(self, allow_test_destinations: bool = False):
        self.webhook_provider = WebhookNotificationProvider(allow_test_destinations=allow_test_destinations)

    def dispatch(
        self,
        recipient: str,
        subject: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, int, str, str]:
        # Wrap into standard Slack webhook payload
        slack_payload = {
            "text": f"🚨 CloudSage FinOps Alert: {subject}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🚨 {payload.get('severity', 'ALERT')}: {subject}"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Provider:*\n{payload.get('provider', 'N/A')}"},
                        {"type": "mrkdwn", "text": f"*Account:*\n{payload.get('account_id', 'N/A')}"},
                        {"type": "mrkdwn", "text": f"*Service:*\n{payload.get('service_name', 'N/A')}"},
                        {"type": "mrkdwn", "text": f"*Excess Spend:*\n+${payload.get('excess_cost', '0.00')} USD (+{payload.get('percentage_deviation', '0')}%)"},
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"_Advisory Only: Review in CloudSage before taking infrastructure actions._"}
                    ]
                }
            ]
        }
        return self.webhook_provider.dispatch(recipient, subject, slack_payload)


class TeamsNotificationProvider(BaseNotificationProvider):
    """Formats and dispatches Microsoft Teams MessageCard payloads."""

    def __init__(self, allow_test_destinations: bool = False):
        self.webhook_provider = WebhookNotificationProvider(allow_test_destinations=allow_test_destinations)

    def dispatch(
        self,
        recipient: str,
        subject: str,
        payload: Dict[str, Any],
    ) -> Tuple[bool, int, str, str]:
        teams_payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": subject,
            "themeColor": "EA4335" if payload.get("severity") == "CRITICAL" else "F2994A",
            "title": f"CloudSage Cost Anomaly: {subject}",
            "sections": [{
                "facts": [
                    {"name": "Provider", "value": str(payload.get("provider", "N/A"))},
                    {"name": "Account", "value": str(payload.get("account_id", "N/A"))},
                    {"name": "Service", "value": str(payload.get("service_name", "N/A"))},
                    {"name": "Excess Cost", "value": f"+${payload.get('excess_cost', '0.00')} USD"},
                    {"name": "Deviation", "value": f"+{payload.get('percentage_deviation', '0')}%"},
                ],
                "text": payload.get("explanation", ""),
            }]
        }
        return self.webhook_provider.dispatch(recipient, subject, teams_payload)
