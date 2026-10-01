"""AIFuzzer Enterprise Alerting & Webhooks Modülü

Fuzzing sırasında bulunan kritik açıkları (Canary sızıntıları, yetkisiz araç çağrıları)
kurumsal bildirim kanallarına (Slack, Microsoft Teams, Discord, Jira) asenkron
HTTP webhook mesajları olarak iletir.
"""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any
from urllib.request import Request, urlopen

logger = logging.getLogger("aifuzzer.alerting")


@dataclass
class AlertPayload:
    event_type: str  # "CANARY_LEAK" | "UNAUTHORIZED_TOOL" | "PRIVILEGE_ESCALATION" | "HIGH_RISK_BYPASS"
    severity: str  # "CRITICAL" | "HIGH" | "MEDIUM"
    test_case_id: str
    target_name: str
    prompt_sample: str
    violation_details: str
    timestamp: str


class EnterpriseAlertDispatcher:
    """Kurumsal kanallara sıfır maliyetle webhook fırlatan bildirim dağıtıcısı."""

    def __init__(self, webhook_url: str | None = None, dry_run: bool = False):
        self.webhook_url = webhook_url
        self.dry_run = dry_run
        self.sent_alerts: list[dict[str, Any]] = []

    def format_slack_card(self, alert: AlertPayload) -> dict[str, Any]:
        """Slack / Discord uyumlu zengin JSON mesaj formatı."""
        return {
            "text": f"[{alert.severity}] AIFuzzer Security Alert: {alert.event_type}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"AIFuzzer Security Finding: {alert.severity}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Event:* `{alert.event_type}`"},
                        {"type": "mrkdwn", "text": f"*Target:* {alert.target_name}"},
                        {"type": "mrkdwn", "text": f"*Test ID:* `{alert.test_case_id}`"},
                        {"type": "mrkdwn", "text": f"*Time:* {alert.timestamp}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Violation Details:*\n```{alert.violation_details}```",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Adversarial Prompt Sample:*\n```{alert.prompt_sample[:250]}...```",
                    },
                },
            ],
        }

    def format_jira_issue_payload(self, alert: AlertPayload, project_key: str = "SEC") -> dict[str, Any]:
        """Atlassian Jira REST API uyumlu issue oluşturma yükü."""
        return {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[AIFuzzer] {alert.severity} vulnerability detected in {alert.target_name} ({alert.event_type})",
                "description": (
                    f"Automated finding detected by AIFuzzer.\n\n"
                    f"Test Case: {alert.test_case_id}\n"
                    f"Severity: {alert.severity}\n"
                    f"Details: {alert.violation_details}\n\n"
                    f"Minimal Adversarial Prompt:\n{alert.prompt_sample}"
                ),
                "issuetype": {"name": "Bug"},
            }
        }

    def send_alert(self, alert: AlertPayload) -> bool:
        """Webhook'a HTTP POST isteği gönderir."""
        formatted_body = self.format_slack_card(alert)
        self.sent_alerts.append(asdict(alert))

        if self.dry_run or not self.webhook_url:
            logger.info("Alert dispatched (dry-run/local mode): %s", alert.event_type)
            return True

        try:
            req_data = json.dumps(formatted_body).encode("utf-8")
            req = Request(
                self.webhook_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=5) as response:
                return 200 <= response.status < 300
        except OSError as e:
            logger.error("Failed to send webhook alert to %s: %s", self.webhook_url, e)
            return False
