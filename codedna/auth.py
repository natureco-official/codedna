"""User authentication — registration, login, JWT session management."""

from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path
from typing import Optional

import bcrypt
import jwt

from codedna.db import get_connection

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# JWT secret MUST come from an environment variable — never hardcoded
JWT_SECRET: Optional[str] = os.environ.get("CODEDNA_JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7   # 7 days

# Auth database path — separate from the repo DB
_AUTH_DB_DEFAULT = Path.home() / ".codedna" / "auth.db"


def _auth_db() -> Path:
    """Return the auth database path (from env var or default)."""
    env = os.environ.get("CODEDNA_AUTH_DB_PATH")
    return Path(env).resolve() if env else _AUTH_DB_DEFAULT


def _check_jwt_secret() -> str:
    """
    Verify that the JWT secret exists.

    The application must not start without a secret in production.
    In development/test, automatically generates a random secret (not persistent).
    """
    secret = JWT_SECRET or os.environ.get("CODEDNA_JWT_SECRET")
    if not secret:
        # Auto-generate a dev secret per process in development mode
        # In production, CODEDNA_JWT_SECRET must be set as an environment variable
        secret = os.environ.get("CODEDNA_JWT_DEV_SECRET")
        if not secret:
            import secrets
            secret = "dev-" + secrets.token_urlsafe(48)
            os.environ["CODEDNA_JWT_DEV_SECRET"] = secret
            import warnings
            warnings.warn(
                "CODEDNA_JWT_SECRET is not set — using a development secret. "
                "Set the CODEDNA_JWT_SECRET environment variable for production.",
                RuntimeWarning,
                stacklevel=2,
            )
    return secret


# ---------------------------------------------------------------------------
# Auth DB schema
# ---------------------------------------------------------------------------

def init_auth_db(db_path: Optional[Path] = None) -> None:
    """Create the users and sessions tables if they do not exist."""
    path = db_path or _auth_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                lemonsqueezy_customer_id TEXT,
                lemonsqueezy_subscription_id TEXT,
                subscription_status TEXT DEFAULT 'none',
                created_at INTEGER,
                updated_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                created_at INTEGER,
                expires_at INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


# ---------------------------------------------------------------------------
# Password operations
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compare a password with a hash in a timing-safe manner."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _token_hash(token: str) -> str:
    """Hash a token with SHA-256 — the token itself is NEVER stored in the DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_jwt(user_id: int, email: str, plan: str) -> str:
    """Generate a JWT token."""
    secret = _check_jwt_secret()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "plan": plan,
        "iat": now,
        "exp": now + JWT_EXPIRY_HOURS * 3600,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str) -> Optional[dict]:
    """Decode a JWT token; return None if invalid."""
    secret = _check_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------------------
# Register / Login / Logout
# ---------------------------------------------------------------------------

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def register_user(
    email: str,
    password: str,
    db_path: Optional[Path] = None,
) -> dict:
    """
    Register a new user.

    Rules:
      - Email format must be valid
      - Password must be at least 8 characters
      - Raises ValueError if the email is already registered

    Args:
        email: User's email address
        password: Plain-text password (not stored after registration)
        db_path: Auth DB path

    Returns:
        {"user_id", "token", "plan"} dict
    """
    path = db_path or _auth_db()
    init_auth_db(path)

    # Input validation
    email = email.strip().lower()
    if not _EMAIL_REGEX.match(email):
        raise ValueError("Invalid email format.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    password_hash = hash_password(password)
    now = int(time.time())

    # Get plan from license file (demo/single-tenant mode)
    # In production, plan is assigned via the purchase flow
    try:
        from codedna.plan import get_current_plan
        initial_plan = get_current_plan().value
    except Exception:
        initial_plan = "free"

    try:
        with get_connection(path) as conn:
            cur = conn.execute(
                """
                INSERT INTO users (email, password_hash, plan, subscription_status, created_at, updated_at)
                VALUES (?, ?, ?, 'demo', ?, ?)
                """,
                (email, password_hash, initial_plan, now, now),
            )
            user_id = cur.lastrowid or 0
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            raise ValueError("This email address is already registered.")
        raise

    token = _create_jwt(user_id, email, initial_plan)
    _save_session(user_id, token, path)

    return {"user_id": user_id, "token": token, "plan": initial_plan}


def login_user(
    email: str,
    password: str,
    db_path: Optional[Path] = None,
) -> dict:
    """
    Log in and generate a JWT token.

    Security note: Do not return specific errors on failed login
    (use a generic message to prevent user enumeration attacks).

    Args:
        email: User's email address
        password: Plain-text password

    Returns:
        {"user_id", "token", "plan", "subscription_status"} dict
    """
    path = db_path or _auth_db()
    init_auth_db(path)

    email = email.strip().lower()

    with get_connection(path) as conn:
        user = conn.execute(
            "SELECT id, password_hash, plan, subscription_status FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    # Same error for missing user or wrong password — prevents user enumeration
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password.")

    token = _create_jwt(user["id"], email, user["plan"])
    _save_session(user["id"], token, path)

    return {
        "user_id": user["id"],
        "token": token,
        "plan": user["plan"],
        "subscription_status": user["subscription_status"],
    }


def verify_token(
    token: str,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """
    Validate a JWT token and return user information.

    Checks both the JWT signature and the session record in the DB.

    Returns:
        {"user_id", "email", "plan"} if valid, None otherwise
    """
    path = db_path or _auth_db()
    payload = _decode_jwt(token)
    if not payload:
        return None

    token_h = _token_hash(token)
    now = int(time.time())

    with get_connection(path) as conn:
        session = conn.execute(
            "SELECT id FROM sessions WHERE token_hash = ? AND expires_at > ?",
            (token_h, now),
        ).fetchone()

    if not session:
        return None

    return {
        "user_id": int(payload["sub"]),
        "email": payload["email"],
        "plan": payload["plan"],
    }


def logout_user(
    token: str,
    db_path: Optional[Path] = None,
) -> bool:
    """
    End the session — delete from the sessions table.

    Returns:
        True if deleted successfully
    """
    path = db_path or _auth_db()
    token_h = _token_hash(token)
    with get_connection(path) as conn:
        cur = conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_h,))
    return cur.rowcount > 0


def get_user_by_id(user_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Fetch user information by ID (excluding the password hash)."""
    path = db_path or _auth_db()
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT id, email, plan, subscription_status, lemonsqueezy_customer_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "plan": row["plan"],
        "subscription_status": row["subscription_status"],
        "lemonsqueezy_customer_id": row["lemonsqueezy_customer_id"],
    }


def update_user_plan(
    user_id: int,
    plan: str,
    subscription_status: str,
    customer_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Update a user's plan and subscription status."""
    path = db_path or _auth_db()
    now = int(time.time())
    with get_connection(path) as conn:
        conn.execute(
            """
            UPDATE users
            SET plan = ?, subscription_status = ?,
                lemonsqueezy_customer_id = COALESCE(?, lemonsqueezy_customer_id),
                lemonsqueezy_subscription_id = COALESCE(?, lemonsqueezy_subscription_id),
                updated_at = ?
            WHERE id = ?
            """,
            (plan, subscription_status, customer_id, subscription_id, now, user_id),
        )


# ---------------------------------------------------------------------------
# Helper — save session
# ---------------------------------------------------------------------------

def _save_session(user_id: int, token: str, db_path: Path) -> None:
    """Save a new session to the DB (only the token hash is stored)."""
    now = int(time.time())
    expires = now + JWT_EXPIRY_HOURS * 3600
    token_h = _token_hash(token)
    with get_connection(db_path) as conn:
        # Clean up old expired sessions
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.execute(
            "INSERT OR IGNORE INTO sessions (user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, token_h, now, expires),
        )
