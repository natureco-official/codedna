"""
Mail monitor — checks Gmail for new important messages.

Uses Gmail IMAP + App Password (stored at ~/.codedna/gmail_app_password, chmod 600).
State persisted at ~/.codedna/mail_state.json (last checked UID + notified count).
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email import policy
from pathlib import Path
from typing import Optional

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
APP_PASSWORD_PATH = Path.home() / ".codedna" / "gmail_app_password"
STATE_PATH = Path.home() / ".codedna" / "mail_state.json"
DEFAULT_USER = "timurhanhz3@gmail.com"

# Keywords that mark a message as important (case-insensitive).
# Each entry: (category, regex pattern, score 1-10)
IMPORTANCE_RULES = [
    # SECURITY (highest priority)
    ("security", r"security alert|token found|token leaked|compromised|breach|vulnerability", 10),
    ("security", r"password.*reset|2fa|two[- ]factor|authentication.*fail", 9),
    ("security", r"suspicious|unauthorized|locked.*account", 9),

    # BILLING / PAYMENTS
    ("billing", r"invoice|payment.*failed|payment.*due|subscription.*renew|billing", 8),
    ("billing", r"expired.*card|card.*declined|refund", 8),

    # INFRASTRUCTURE / DEPLOYMENT
    ("infra", r"deploy.*fail|build.*fail|crash|error.*production|outage|downtime", 8),
    ("infra", r"ci.*fail|github actions.*fail|vercel.*deploy|cloudflare.*error", 7),
    ("infra", r"domain.*expire|ssl.*expir|renew.*domain", 7),

    # PROJECT NOTIFICATIONS (npm, PyPI, GitHub)
    ("project", r"npm security alert|npm token found", 10),  # explicit override
    ("project", r"published|release|deployment|build success", 4),
    ("project", r"github|npm|pypi|docker|vercel", 3),

    # BUSINESS / CLIENT
    ("business", r"meeting|call|interview|proposal|contract|client", 6),
    ("business", r"invoice.*sent|quote|estimate", 5),

    # SOCIAL (low priority)
    ("social", r"@.*|commented|liked|shared|invited", 1),
]

# Noise keywords (auto-skip)
NOISE_PATTERNS = [
    r"^Re: ",
    r"newsletter|digest|weekly update",
    r"marketing|promotion|sale \d+%",
    r"noreply|no-reply@",
    r"verify your email|confirm your email",  # Often auto-generated
]


@dataclass
class MailMessage:
    """A parsed Gmail message."""
    uid: str
    from_addr: str
    subject: str
    date: str
    body_preview: str
    importance_score: int = 0
    importance_category: str = ""
    is_noise: bool = False


@dataclass
class MailCheckResult:
    """Result of mail check operation."""
    total_new: int = 0
    important: list[MailMessage] = field(default_factory=list)
    noise: list[MailMessage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _load_state() -> dict:
    """Load mail check state (last UID, etc.)."""
    if not STATE_PATH.exists():
        return {"last_uid": "0", "last_check": None, "history": []}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"last_uid": "0", "last_check": None, "history": []}


def _save_state(state: dict) -> None:
    """Persist mail check state."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    try:
        os.chmod(STATE_PATH, 0o600)
    except OSError:
        pass


def _score_message(msg: MailMessage) -> None:
    """Score a message for importance based on subject + body."""
    text = f"{msg.subject} {msg.body_preview}".lower()

    # Noise detection
    for pat in NOISE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            msg.is_noise = True
            return

    # Importance scoring (take max)
    max_score = 0
    best_cat = ""
    for cat, pat, score in IMPORTANCE_RULES:
        if re.search(pat, text, re.IGNORECASE):
            if score > max_score:
                max_score = score
                best_cat = cat
    msg.importance_score = max_score
    msg.importance_category = best_cat


def _connect(user: str = DEFAULT_USER) -> imaplib.IMAP4_SSL:
    """Connect to Gmail IMAP using App Password."""
    if not APP_PASSWORD_PATH.exists():
        raise FileNotFoundError(
            f"Gmail App Password not found at {APP_PASSWORD_PATH}. "
            f"Save the 16-char app password there with chmod 600."
        )
    password = APP_PASSWORD_PATH.read_text().strip()
    imap = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST, GMAIL_IMAP_PORT)
    imap.login(user, password)
    return imap


def _fetch_new_messages(imap: imaplib.IMAP4_SSL, since_days: int = 1) -> list[MailMessage]:
    """Fetch new messages from the last N days."""
    imap.select("INBOX")
    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
    status, msg_ids = imap.search(None, f"SINCE {since_date}")
    if not msg_ids[0]:
        return []

    messages = []
    for mid_bytes in msg_ids[0].split():
        mid = mid_bytes.decode()
        status, msg_data = imap.fetch(mid_bytes, "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        try:
            parsed = email.message_from_bytes(raw, policy=policy.default)
        except Exception:
            continue

        # Body preview (first 500 chars of text/plain)
        body_preview = ""
        if parsed.is_multipart():
            for part in parsed.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_preview = (part.get_content() or "")[:500]
                        break
                    except Exception:
                        pass
        else:
            try:
                body_preview = (parsed.get_content() or "")[:500]
            except Exception:
                pass

        msg = MailMessage(
            uid=mid,
            from_addr=parsed.get("From", "?"),
            subject=parsed.get("Subject", "(no subject)"),
            date=parsed.get("Date", "?"),
            body_preview=body_preview,
        )
        _score_message(msg)
        messages.append(msg)
    return messages


def check_mail(since_days: int = 1, threshold: int = 5) -> MailCheckResult:
    """Check Gmail for new important messages.

    Args:
        since_days: Look back N days (default: 1)
        threshold: Min importance score to be "important" (default: 5)

    Returns:
        MailCheckResult with total count, important, and noise messages.
    """
    result = MailCheckResult()
    try:
        imap = _connect()
    except Exception as e:
        result.errors.append(f"connect failed: {e}")
        return result

    try:
        all_msgs = _fetch_new_messages(imap, since_days=since_days)
    except Exception as e:
        result.errors.append(f"fetch failed: {e}")
        imap.logout()
        return result

    imap.logout()

    # Filter: noise skipped, important >= threshold
    for m in all_msgs:
        if m.is_noise:
            result.noise.append(m)
        elif m.importance_score >= threshold:
            result.important.append(m)
        else:
            result.noise.append(m)

    result.total_new = len(all_msgs)
    return result


def format_report(result: MailCheckResult, threshold: int = 5) -> str:
    """Format mail check result as a readable report."""
    lines = []
    lines.append(f"📬 Mail Check — {result.total_new} new message(s)")
    if result.errors:
        lines.append(f"⚠ Errors: {len(result.errors)}")
        for e in result.errors:
            lines.append(f"  - {e}")
    if result.important:
        lines.append(f"\n🔥 Important ({len(result.important)}):")
        for m in result.important:
            lines.append(f"  [{m.importance_category}] score={m.importance_score}")
            lines.append(f"    From: {m.from_addr}")
            lines.append(f"    Subject: {m.subject}")
            lines.append(f"    Date: {m.date}")
            if m.body_preview:
                preview = m.body_preview[:200].replace("\n", " ")
                lines.append(f"    Preview: {preview}...")
    if result.noise:
        lines.append(f"\n📭 Noise ({len(result.noise)}): skipped")
    return "\n".join(lines)


def get_new_since_last_check() -> MailCheckResult:
    """Check Gmail for messages newer than the last seen UID."""
    state = _load_state()
    last_uid = state.get("last_uid", "0")

    result = MailCheckResult()
    try:
        imap = _connect()
        imap.select("INBOX")
        # Get all UIDs
        status, all_uids = imap.uid("SEARCH", None, "ALL")
        if not all_uids[0]:
            imap.logout()
            return result

        uids = all_uids[0].split()
        if last_uid in uids:
            # Find new ones after last_uid
            last_idx = uids.index(last_uid)
            new_uids = uids[last_idx + 1:]
        else:
            new_uids = uids

        if not new_uids:
            imap.logout()
            return result

        # Fetch new ones
        for uid_bytes in new_uids:
            uid_str = uid_bytes.decode()
            status, msg_data = imap.uid("FETCH", uid_bytes, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            try:
                parsed = email.message_from_bytes(raw, policy=policy.default)
            except Exception:
                continue

            body_preview = ""
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body_preview = (part.get_content() or "")[:500]
                            break
                        except Exception:
                            pass
            else:
                try:
                    body_preview = (parsed.get_content() or "")[:500]
                except Exception:
                    pass

            msg = MailMessage(
                uid=uid_str,
                from_addr=parsed.get("From", "?"),
                subject=parsed.get("Subject", "(no subject)"),
                date=parsed.get("Date", "?"),
                body_preview=body_preview,
            )
            _score_message(msg)

            if msg.is_noise:
                result.noise.append(msg)
            elif msg.importance_score >= 5:
                result.important.append(msg)
            else:
                result.noise.append(msg)

        # Update state to highest UID
        new_max = max(int(u) for u in uids)
        state["last_uid"] = str(new_max)
        state["last_check"] = datetime.now().isoformat()
        _save_state(state)

        imap.logout()
    except Exception as e:
        result.errors.append(f"check failed: {e}")

    result.total_new = len(result.important) + len(result.noise)
    return result
