"""Tests for the webhooks module."""

from pathlib import Path
from codedna.webhooks import WebhookConfig, send_notification, notify_scan_result


def test_webhook_config_defaults():
    config = WebhookConfig()
    assert config.slack_url is None
    assert config.discord_url is None
    assert config.enabled is True
    assert config.min_ai_risk == 0.7
    assert "high_risk" in config.notify_on


def test_webhook_config_save_load(tmp_path, monkeypatch):
    monkeypatch.setattr("codedna.webhooks.WEBHOOK_CONFIG_PATH", tmp_path / "webhooks.json")
    config = WebhookConfig(
        slack_url="https://hooks.slack.com/test",
        discord_url="https://discord.com/api/webhooks/test",
        enabled=True,
        min_ai_risk=0.8,
    )
    config.save()

    loaded = WebhookConfig.load()
    assert loaded.slack_url == "https://hooks.slack.com/test"
    assert loaded.discord_url == "https://discord.com/api/webhooks/test"
    assert loaded.enabled is True
    assert loaded.min_ai_risk == 0.8


def test_webhook_config_disabled():
    config = WebhookConfig(enabled=False)
    errors = send_notification("Test", "Message", config)
    assert errors == []


def test_notify_scan_result_disabled(monkeypatch):
    monkeypatch.setattr("codedna.webhooks.WEBHOOK_CONFIG_PATH", Path("/nonexistent/webhooks.json"))
    errors = notify_scan_result(
        avg_ai=0.5,
        max_ai=0.5,
        repo_name="test-repo",
    )
    assert errors == []


def test_notify_scan_result_with_violations(monkeypatch):
    monkeypatch.setattr("codedna.webhooks.WEBHOOK_CONFIG_PATH", Path("/nonexistent/webhooks.json"))
    errors = notify_scan_result(
        avg_ai=0.3,
        max_ai=0.3,
        repo_name="test-repo",
        violations=["File X: understanding below threshold"],
    )
    assert errors == []


def test_webhook_config_min_risk_not_triggered(monkeypatch):
    monkeypatch.setattr("codedna.webhooks.WEBHOOK_CONFIG_PATH", Path("/nonexistent/webhooks.json"))
    errors = notify_scan_result(
        avg_ai=0.3,
        max_ai=0.3,
        min_ai_risk=0.7,
        repo_name="test-repo",
    )
    assert errors == []
