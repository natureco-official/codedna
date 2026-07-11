"""Webhook notification system for Slack and Discord."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

WEBHOOK_CONFIG_PATH = Path.home() / ".codedna" / "webhooks.json"


@dataclass
class WebhookConfig:
    slack_url: Optional[str] = None
    discord_url: Optional[str] = None
    enabled: bool = True
    min_ai_risk: float = 0.7
    notify_on: list[str] = field(default_factory=lambda: ["high_risk", "violation"])

    @classmethod
    def load(cls) -> "WebhookConfig":
        if not WEBHOOK_CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(WEBHOOK_CONFIG_PATH.read_text())
            return cls(
                slack_url=data.get("slack_url"),
                discord_url=data.get("discord_url"),
                enabled=data.get("enabled", True),
                min_ai_risk=data.get("min_ai_risk", 0.7),
                notify_on=data.get("notify_on", ["high_risk", "violation"]),
            )
        except Exception:
            return cls()

    def save(self) -> None:
        WEBHOOK_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        WEBHOOK_CONFIG_PATH.write_text(
            json.dumps({
                "slack_url": self.slack_url,
                "discord_url": self.discord_url,
                "enabled": self.enabled,
                "min_ai_risk": self.min_ai_risk,
                "notify_on": self.notify_on,
            }, indent=2)
        )


def _send_slack(webhook_url: str, message: str) -> None:
    payload = {"text": message}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def _send_discord(webhook_url: str, message: str) -> None:
    payload = {"content": message}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def send_notification(
    title: str,
    message: str,
    config: Optional[WebhookConfig] = None,
) -> list[str]:
    if config is None:
        config = WebhookConfig.load()
    if not config.enabled:
        return []

    errors: list[str] = []
    formatted = f"*{title}*\n{message}"

    if config.slack_url:
        try:
            _send_slack(config.slack_url, formatted)
        except Exception as e:
            errors.append(f"Slack: {e}")

    if config.discord_url:
        try:
            _send_discord(config.discord_url, formatted)
        except Exception as e:
            errors.append(f"Discord: {e}")

    return errors


def notify_scan_result(
    avg_ai: float,
    max_ai: float,
    min_ai_risk: float = 0.7,
    repo_name: str = "unknown",
    commit_hash: Optional[str] = None,
    violations: Optional[list[str]] = None,
) -> list[str]:
    """Check risk thresholds and send notifications if exceeded."""
    config = WebhookConfig.load()
    if not config.enabled:
        return []

    errors: list[str] = []
    commit_short = commit_hash[:8] if commit_hash else "?"

    if "high_risk" in config.notify_on and max_ai >= config.min_ai_risk:
        title = "High AI Risk Detected"
        message = (
            f"Repository: {repo_name}\n"
            f"Commit: {commit_short}\n"
            f"Max AI Probability: {max_ai * 100:.0f}%\n"
            f"Avg AI Probability: {avg_ai * 100:.0f}%\n"
        )
        errors.extend(send_notification(title, message, config))

    if "violation" in config.notify_on and violations:
        title = "Protected Module Violation"
        message = (
            f"Repository: {repo_name}\n"
            f"Commit: {commit_short}\n"
            f"Violations:\n" + "\n".join(f"  \u2022 {v}" for v in violations)
        )
        errors.extend(send_notification(title, message, config))

    return errors
