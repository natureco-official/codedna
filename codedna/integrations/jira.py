"""Maps Jira sprint data to CodeDNA sprint records."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Webhook secret file
_SECRET_FILE = Path.home() / ".codedna" / "jira_secret.txt"


# ---------------------------------------------------------------------------
# Webhook Secret Management
# ---------------------------------------------------------------------------

def get_or_create_secret() -> str:
    """
    Read the Jira webhook secret or create a new one if it doesn't exist.

    Returns:
        32-byte secret in hex format
    """
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_FILE.write_text(secret)
    return secret


def rotate_secret() -> str:
    """Rotate the webhook secret and return the new value."""
    new_secret = secrets.token_hex(32)
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_FILE.write_text(new_secret)
    return new_secret


def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify a Jira webhook signature using HMAC-SHA256.

    Jira signature format: "sha256=<hex_digest>"

    Args:
        payload_bytes: Raw HTTP body
        signature_header: X-Hub-Signature-256 header value
        secret: Webhook secret

    Returns:
        True if the signature is valid
    """
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[7:]
    computed = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected)


# ---------------------------------------------------------------------------
# Webhook Processing
# ---------------------------------------------------------------------------

def handle_jira_webhook(payload: dict[str, Any], db_path: Path) -> dict[str, Any]:
    """
    Process a Jira webhook payload and create/update a sprint record.

    Supported event types:
      - sprint_started: New sprint started → create record
      - sprint_closed:  Sprint closed → calculate health score + update

    Args:
        payload: Jira webhook JSON payload
        db_path: SQLite database path

    Returns:
        Dict with operation result
    """
    event_type = payload.get("webhookEvent", "")
    sprint_data = payload.get("sprint", {})

    if not sprint_data:
        return {"status": "skipped", "reason": "no sprint data"}

    sprint_name = sprint_data.get("name", "Jira Sprint")
    start_str = sprint_data.get("startDate") or sprint_data.get("activatedDate")
    end_str = sprint_data.get("endDate") or sprint_data.get("completeDate")

    start = _parse_date(start_str)
    end = _parse_date(end_str)

    if not start or not end:
        return {"status": "error", "reason": "missing date information"}

    if event_type in ("sprint_started", "jira:sprint_created"):
        # Sprint started — create record (health score not yet calculated)
        from codedna.db import save_sprint
        sprint_id = save_sprint(
            sprint_name=sprint_name,
            start_date=int(start.timestamp()),
            end_date=int(end.timestamp()),
            total_lines_ai=0,
            total_lines_human=0,
            avg_understanding=None,
            debt_delta_hours=None,
            health_score=None,
            db_path=db_path,
        )
        return {
            "status": "created",
            "sprint_id": sprint_id,
            "sprint_name": sprint_name,
        }

    elif event_type in ("sprint_closed", "jira:sprint_completed"):
        # Sprint closed — calculate health score
        from codedna.sprint_health import calculate_sprint_health, save_sprint_result
        from codedna.git_hook import find_git_root

        repo_root = find_git_root() or Path.cwd()
        try:
            result = calculate_sprint_health(repo_root, db_path, start, end, sprint_name)
            sprint_id = save_sprint_result(result, db_path)
            return {
                "status": "completed",
                "sprint_id": sprint_id,
                "sprint_name": sprint_name,
                "health_score": result.health_score,
                "sprint_status": result.status,
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    return {"status": "skipped", "reason": f"unsupported event: {event_type}"}


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse Jira date strings into datetime.
    Supported formats: ISO 8601 and common variants.
    """
    if not date_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:len(fmt) + 5], fmt)
        except ValueError:
            continue
    return None
