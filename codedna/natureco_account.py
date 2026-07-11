"""NatureCo Account (SSO) — one NatureCo account, ecosystem-wide.

Shares the same session file (``~/.natureco/auth.json``) with the NatureCo CLI
and Cupertino Terminal, so signing in once works everywhere. Built on the
natureco.me Supabase Auth REST API. Dependency-free (standard-library urllib);
the anon key is public (embedded in every client, not a secret).
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# natureco.me identity project — anon key is PUBLIC (shipped in clients, not secret)
SUPABASE_URL = os.environ.get("NATURECO_SUPABASE_URL", "https://mxnlehflfkesasclcldy.supabase.co")
SUPABASE_ANON = os.environ.get(
    "NATURECO_SUPABASE_ANON",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im14bmxlaGZsZmtlc2FzY2xjbGR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2NDA5MzEsImV4cCI6MjA5MjIxNjkzMX0.93aPOg6bVmgFaJvsM5jVZwiX2TTuFIyAzhP6BlhBkGU",
)
AUTH_BASE = f"{SUPABASE_URL}/auth/v1"


class NatureCoAuthError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _auth_file() -> Path:
    return Path.home() / ".natureco" / "auth.json"


def load_session() -> dict | None:
    try:
        return json.loads(_auth_file().read_text(encoding="utf-8"))
    except Exception:
        return None


def save_session(session: dict) -> dict:
    f = _auth_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(session, indent=2), encoding="utf-8")
    try:
        os.chmod(f, 0o600)
    except Exception:
        pass
    return session


def clear_session() -> None:
    try:
        _auth_file().unlink()
    except Exception:
        pass


def _post(path: str, body: dict, access_token: str | None = None) -> dict:
    headers = {"apikey": SUPABASE_ANON, "Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    req = urllib.request.Request(
        f"{AUTH_BASE}{path}", data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode())
        except Exception:
            data = {}
        msg = data.get("error_description") or data.get("msg") or data.get("error") or f"Auth error ({e.code})"
        raise NatureCoAuthError(msg, e.code) from e


def _shape(s: dict) -> dict:
    expires_at = s.get("expires_at") or (int(time.time()) + s["expires_in"] if s.get("expires_in") else None)
    user = s.get("user")
    return {
        "access_token": s.get("access_token"),
        "refresh_token": s.get("refresh_token"),
        "token_type": s.get("token_type", "bearer"),
        "expires_at": expires_at,
        "user": {"id": user["id"], "email": user["email"]} if user else None,
    }


def _user_from_jwt(token: str) -> dict | None:
    """Decode the user out of the access token (no signature check — display only)."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        p = json.loads(base64.urlsafe_b64decode(part))
        return {"id": p.get("sub"), "email": p.get("email")}
    except Exception:
        return None


def login_with_password(email: str, password: str) -> dict:
    return save_session(_shape(_post("/token?grant_type=password", {"email": email, "password": password})))


def send_otp(email: str) -> dict:
    """Passwordless: send a code / login link to the email (existing account only)."""
    _post("/otp", {"email": email, "create_user": False})
    return {"sent": True, "email": email}


def verify_otp(email: str, token: str) -> dict:
    """Verify the OTP code. Depending on the email template the verification type
    may be 'email' or 'magiclink', so both are attempted."""
    code = "".join(str(token).split())
    try:
        return save_session(_shape(_post("/verify", {"type": "email", "email": email, "token": code})))
    except NatureCoAuthError as e1:
        try:
            return save_session(_shape(_post("/verify", {"type": "magiclink", "email": email, "token": code})))
        except Exception:
            raise e1


def verify_link(link: str) -> dict:
    """Sign in from a magic login-link email. Handles both the implicit flow
    (access_token in the URL fragment) and the token_hash flow."""
    u = urlparse(link.strip())
    frag = parse_qs(u.fragment)
    q = parse_qs(u.query)

    def pick(k: str):
        return (frag.get(k) or q.get(k) or [None])[0]

    access_token = pick("access_token")
    if access_token:
        return save_session(_shape({
            "access_token": access_token,
            "refresh_token": pick("refresh_token"),
            "token_type": pick("token_type") or "bearer",
            "expires_at": int(pick("expires_at") or 0) or None,
            "expires_in": int(pick("expires_in") or 0) or None,
            "user": _user_from_jwt(access_token),
        }))
    token_hash = pick("token_hash") or pick("token")
    typ = pick("type") or "magiclink"
    if not token_hash:
        raise NatureCoAuthError("No verification token found in the link")
    return save_session(_shape(_post("/verify", {"type": typ, "token_hash": token_hash})))


def refresh() -> dict:
    s = load_session()
    if not s or not s.get("refresh_token"):
        raise NatureCoAuthError("Not signed in", 401)
    return save_session(_shape(_post("/token?grant_type=refresh_token", {"refresh_token": s["refresh_token"]})))


def get_access_token() -> str | None:
    s = load_session()
    if not s:
        return None
    if s.get("expires_at") and time.time() > s["expires_at"] - 60:
        try:
            s = refresh()
        except Exception:
            return None
    return s.get("access_token") if s else None


def whoami() -> dict | None:
    token = get_access_token()
    if not token:
        return None
    req = urllib.request.Request(
        f"{AUTH_BASE}/user", headers={"apikey": SUPABASE_ANON, "Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def is_logged_in() -> bool:
    s = load_session()
    return bool(s and s.get("access_token"))


def current_email() -> str | None:
    s = load_session()
    return s.get("user", {}).get("email") if s and s.get("user") else None


def logout() -> None:
    clear_session()
