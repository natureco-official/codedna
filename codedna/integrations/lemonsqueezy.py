"""Lemon Squeezy checkout and subscription webhook integration."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Environment variables — never hardcoded
# ---------------------------------------------------------------------------

LEMONSQUEEZY_API_KEY      = os.environ.get("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_WEBHOOK_SECRET = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET")
LEMONSQUEEZY_STORE_ID     = os.environ.get("LEMONSQUEEZY_STORE_ID")

# Plan → Lemon Squeezy variant ID mapping (real IDs come from .env)
PLAN_VARIANT_MAP: dict[str, Optional[str]] = {
    "pro":        os.environ.get("LS_VARIANT_PRO"),
    "team":       os.environ.get("LS_VARIANT_TEAM"),
    "enterprise": os.environ.get("LS_VARIANT_ENTERPRISE"),
}

# Lemon Squeezy API base URL
_LS_API_BASE = "https://api.lemonsqueezy.com/v1"


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify a Lemon Squeezy webhook signature using HMAC-SHA256.

    Lemon Squeezy sends a hex digest in the X-Signature header.
    Uses hmac.compare_digest for timing-safe comparison.

    Args:
        payload: Raw HTTP body (bytes)
        signature: X-Signature header value

    Returns:
        True if the signature is valid
    """
    secret = LEMONSQUEEZY_WEBHOOK_SECRET
    if not secret:
        return False

    computed = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


# ---------------------------------------------------------------------------
# Checkout URL creation
# ---------------------------------------------------------------------------

def create_checkout_url(
    plan: str,
    user_email: str,
    user_id: int,
) -> str:
    """
    Request the Lemon Squeezy Checkout API and return the hosted checkout URL.

    user_id is embedded in custom_data to match the webhook to the correct user.

    Docs: https://docs.lemonsqueezy.com/api/checkouts

    Args:
        plan: "pro" | "team" | "enterprise"
        user_email: User's email address (pre-filled in checkout)
        user_id: User ID (for webhook matching)

    Returns:
        Checkout URL string

    Raises:
        ValueError: If API key or variant ID is missing
        RuntimeError: If the API request fails
    """
    import urllib.request
    import urllib.error

    api_key    = LEMONSQUEEZY_API_KEY
    store_id   = LEMONSQUEEZY_STORE_ID
    variant_id = PLAN_VARIANT_MAP.get(plan)

    if not api_key:
        raise ValueError(
            "LEMONSQUEEZY_API_KEY environment variable is not set. "
            "See .env.example."
        )
    if not store_id:
        raise ValueError("LEMONSQUEEZY_STORE_ID environment variable is not set.")
    if not variant_id:
        raise ValueError(
            f"LS_VARIANT_{plan.upper()} environment variable is not set."
        )

    body = json.dumps({
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user_email,
                    "custom": {"user_id": str(user_id)},
                },
            },
            "relationships": {
                "store":   {"data": {"type": "stores",   "id": str(store_id)}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{_LS_API_BASE}/checkouts",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read())
            return data["data"]["attributes"]["url"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Lemon Squeezy API error ({e.code}): {error_body}")
    except Exception as e:
        raise RuntimeError(f"Could not create checkout URL: {e}")


# ---------------------------------------------------------------------------
# Webhook event handling
# ---------------------------------------------------------------------------

# LS event → (plan, subscription_status) mapping
_EVENT_STATUS_MAP: dict[str, tuple[Optional[str], str]] = {
    "subscription_created":        (None,   "active"),     # plan determined from custom_data
    "subscription_updated":        (None,   "active"),
    "subscription_cancelled":      (None,   "cancelled"),  # plan not immediately downgraded
    "subscription_expired":        ("free", "none"),
    "subscription_payment_failed": (None,   "past_due"),
}


def handle_subscription_webhook(
    payload: dict,
    db_path: Path,
) -> dict:
    """
    Process Lemon Squeezy webhook events and update the user's plan.

    user_id from custom_data is used to match the user for all events.

    Args:
        payload: Webhook JSON payload
        db_path: Auth DB path

    Returns:
        Dict with operation result
    """
    from codedna.auth import update_user_plan, init_auth_db

    init_auth_db(db_path)

    event_type = payload.get("meta", {}).get("event_name", "")
    if event_type not in _EVENT_STATUS_MAP:
        return {"status": "skipped", "event": event_type}

    # Get user ID from custom_data
    custom_data = payload.get("meta", {}).get("custom_data", {})
    user_id_str = custom_data.get("user_id")
    if not user_id_str:
        return {"status": "error", "reason": "custom_data.user_id missing"}

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return {"status": "error", "reason": f"Invalid user_id: {user_id_str!r}"}

    # Get subscription data
    subscription = payload.get("data", {}).get("attributes", {})
    customer_id    = str(subscription.get("customer_id", "")) or None
    subscription_id = str(payload.get("data", {}).get("id", "")) or None

    # Determine plan
    new_plan, new_status = _EVENT_STATUS_MAP[event_type]

    # For subscription_created/updated, determine plan from variant
    if new_plan is None:
        variant_id = str(subscription.get("variant_id", ""))
        for plan_name, vid in PLAN_VARIANT_MAP.items():
            if vid and vid == variant_id:
                new_plan = plan_name
                break
        if new_plan is None:
            new_plan = "pro"  # unknown variant → default to pro

    update_user_plan(
        user_id=user_id,
        plan=new_plan,
        subscription_status=new_status,
        customer_id=customer_id,
        subscription_id=subscription_id,
        db_path=db_path,
    )

    return {
        "status": "updated",
        "user_id": user_id,
        "new_plan": new_plan,
        "subscription_status": new_status,
        "event": event_type,
    }
