"""Plan management — plan level is determined by license key."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Optional


class Plan(str, Enum):
    """Available plan levels."""

    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


# License file path
_LICENSE_PATH = Path.home() / ".codedna" / "license.json"

# Feature → allowed plans mapping
_FEATURE_PLANS: dict[str, list[Plan]] = {
    "unlimited_repos":  [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "unlimited_files":  [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "history_90d":      [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "history_365d":     [Plan.TEAM, Plan.ENTERPRISE],
    "dashboard_access": [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "github_actions":   [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    "slack_notify":     [Plan.TEAM, Plan.ENTERPRISE],
    "bus_factor":       [Plan.TEAM, Plan.ENTERPRISE],
    "sprint_health":    [Plan.TEAM, Plan.ENTERPRISE],
    "ai_comparison":    [Plan.ENTERPRISE],
    "interview_tool":   [Plan.ENTERPRISE],
    # NatureCo CLI integration — Pro+ feature
    "natureco_integration": [Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
}

# Features accessible on all plans (default)
_PUBLIC_FEATURES: set[str] = {
    "scan", "history_7d", "cli_basic",
}


def get_current_plan() -> Plan:
    """
    Read plan from ~/.codedna/license.json.

    Returns FREE if the file does not exist.
    Format: {"plan": "pro", "key": "...", "expires": "2027-01-01"}
    """
    if not _LICENSE_PATH.exists():
        return Plan.FREE
    try:
        data = json.loads(_LICENSE_PATH.read_text(encoding="utf-8"))
        return Plan(data.get("plan", "free"))
    except Exception:
        return Plan.FREE


def is_feature_available(feature: str, plan: Optional[Plan] = None) -> bool:
    """
    Check whether a feature is available on the current plan.

    Args:
        feature: Feature name to check
        plan: Plan level (reads current plan if None)

    Returns:
        True if the feature is available
    """
    if plan is None:
        plan = get_current_plan()

    # Features open to everyone
    if feature in _PUBLIC_FEATURES:
        return True

    return plan in _FEATURE_PLANS.get(
        feature,
        [Plan.FREE, Plan.PRO, Plan.TEAM, Plan.ENTERPRISE],
    )


def activate_license(key: str) -> Plan:
    """
    Validate and activate a license key.

    Note: Lemon Squeezy does not provide a license key API — purchases are
    made via checkout URL, and subscription_status is updated via webhook.

    For now, determines plan based on key format:
      - 'CDNA-PRO-...'  → pro
      - 'CDNA-TEAM-...' → team
      - 'CDNA-ENT-...'  → enterprise

    Args:
        key: License key

    Returns:
        Activated plan level
    """
    normalized = key.upper().strip()

    if normalized.startswith("CDNA-PRO"):
        plan = Plan.PRO
    elif normalized.startswith("CDNA-TEAM"):
        plan = Plan.TEAM
    elif normalized.startswith("CDNA-ENT"):
        plan = Plan.ENTERPRISE
    else:
        raise ValueError(f"Invalid license key format: {key!r}")

    _write_license_file(plan, normalized)
    return plan


def _write_license_file(plan: Plan, key: str) -> None:
    """Write the license file."""
    _LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LICENSE_PATH.write_text(
        json.dumps({"plan": plan.value, "key": key}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def activate_demo_license(plan: Plan) -> Plan:
    """
    Activate a demo license — no real key required.

    For development, demo, CI/CD, and testing.
    Valid for 7 days; can be renewed with `codedna plan demo`.

    Args:
        plan: Target plan (free, pro, team, enterprise)

    Returns:
        Activated plan
    """
    import secrets as _secrets

    now = int(__import__("time").time())
    expires = now + (7 * 24 * 3600)  # 7 days

    # Random demo key (mimics real format)
    demo_key = f"CDNA-{plan.value.upper()[:3]}-DEMO-{_secrets.token_urlsafe(16).upper()}"

    _LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LICENSE_PATH.write_text(
        json.dumps(
            {
                "plan": plan.value,
                "key": demo_key,
                "expires": __import__("datetime").datetime.fromtimestamp(expires).strftime("%Y-%m-%d"),
                "demo": True,
                "activated_at": now,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return plan


def get_plan_limits() -> dict[str, object]:
    """Return the limit values for the current plan."""
    plan = get_current_plan()
    limits: dict[str, object] = {
        Plan.FREE: {
            "max_repos": 1, "max_files_scan": 50, "history_days": 7,
            "dashboard_access": False, "github_actions": False,
        },
        Plan.PRO: {
            "max_repos": -1, "max_files_scan": -1, "history_days": 90,
            "dashboard_access": True, "github_actions": True,
        },
        Plan.TEAM: {
            "max_repos": -1, "max_files_scan": -1, "history_days": 365,
            "dashboard_access": True, "github_actions": True,
            "slack_notify": True, "bus_factor": True,
        },
        Plan.ENTERPRISE: {
            "max_repos": -1, "max_files_scan": -1, "history_days": -1,
            "dashboard_access": True, "github_actions": True,
            "slack_notify": True, "bus_factor": True,
            "sprint_health": True, "ai_comparison": True,
        },
    }
    return limits.get(plan, limits[Plan.FREE])  # type: ignore[return-value]
