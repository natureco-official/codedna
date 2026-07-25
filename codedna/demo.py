"""
Demo mode — seeds the database with realistic fake data for new users.

Does NOT perform real code analysis.
All data is deterministic (random.seed(42)) and tagged with '__demo__' prefix.
"""
from __future__ import annotations

import json
import random
import sqlite3
import time
from pathlib import Path
from typing import Optional

DEMO_COMMIT_PREFIX = "__demo__"

# ── Seed data ───────────────────────────────────────────────────────────
AUTHORS = [
    "alice@example.com",
    "bob@example.com",
    "carol@example.com",
    "dave@example.com",
]

FILES = [
    "src/auth/handler.py",
    "src/api/routes.py",
    "src/utils/helpers.py",
    "src/db/models.py",
    "tests/test_auth.py",
    "tests/test_api.py",
    "src/payments/checkout.py",
    "src/notifications/email.py",
]

SPRINT_NAMES = ["Sprint 23 — Auth refactor", "Sprint 24 — API v2", "Sprint 25 — Payments"]


# ── Helpers ────────────────────────────────────────────────────────────
def is_demo_active(db_path: Path) -> bool:
    """Return True if demo data exists in the database."""
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM commits WHERE commit_hash LIKE ?",
                (f"{DEMO_COMMIT_PREFIX}%",),
            ).fetchone()
            return bool(row and row[0] > 0)
    except sqlite3.DatabaseError:
        return False


def clear_demo_data(db_path: Path) -> int:
    """Remove all demo rows. Returns number of rows deleted."""
    if not db_path.exists():
        return 0
    deleted = 0
    with sqlite3.connect(str(db_path)) as conn:
        # file_scores first (FK to commits)
        cur = conn.execute(
            "DELETE FROM file_scores WHERE commit_hash LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        )
        deleted += cur.rowcount
        cur = conn.execute(
            "DELETE FROM commits WHERE commit_hash LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        )
        deleted += cur.rowcount
        cur = conn.execute(
            "DELETE FROM file_ownership WHERE file_path LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        )
        deleted += cur.rowcount
        cur = conn.execute(
            "DELETE FROM sprints WHERE sprint_name LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        )
        deleted += cur.rowcount
        conn.commit()
    return deleted


def _rand_understanding() -> Optional[float]:
    """Realistic understanding distribution: 20% null, 80% in [3.0, 5.0]."""
    if random.random() < 0.2:
        return None
    return round(random.uniform(3.0, 5.0), 2)


def _rand_ai_probability() -> float:
    """AI probability varies 0.1–0.9."""
    return round(random.uniform(0.1, 0.9), 2)


def _complexity_label(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _complexity_score() -> float:
    return round(random.uniform(20.0, 90.0), 1)


def _commit_hash(idx: int) -> str:
    return f"{DEMO_COMMIT_PREFIX}{idx:04d}"


# ── Main seeder ────────────────────────────────────────────────────────
def seed_demo_data(db_path: Path) -> dict:
    """
    Seed database with demo data. Idempotent — skips if demo data already exists.
    Returns: {"commits": N, "files": N, "authors": N, "sprints": N}
    """
    random.seed(42)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Make sure schema exists
    from codedna.db import init_db
    init_db(db_path)

    if is_demo_active(db_path):
        existing = _count_demo(db_path)
        existing["status"] = "already_seeded"
        return existing

    now = int(time.time())
    day = 24 * 60 * 60

    with sqlite3.connect(str(db_path)) as conn:
        # ── Commits (47 over last 30 days) ─────────────────────────────
        commit_hashes: list[str] = []
        for i in range(47):
            ch = _commit_hash(i)
            commit_hashes.append(ch)
            author = random.choice(AUTHORS)
            ts = now - random.randint(0, 30) * day - random.randint(0, 86400)
            files_changed = random.randint(1, 4)
            understanding = _rand_understanding()
            conn.execute(
                """INSERT INTO commits (commit_hash, author, timestamp, files_changed, understanding_score)
                   VALUES (?, ?, ?, ?, ?)""",
                (ch, author, ts, files_changed, understanding),
            )

            # file_scores for this commit (1–3 files per commit)
            n_files = random.randint(1, 3)
            for _ in range(n_files):
                fpath = random.choice(FILES)
                ai_p = _rand_ai_probability()
                cx = _complexity_score()
                cmt_ratio = round(random.uniform(0.05, 0.25), 2)
                conn.execute(
                    """INSERT INTO file_scores
                       (commit_hash, file_path, ai_probability, complexity_score,
                        comment_ratio, understanding_score, ai_tool_guess)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ch,
                        fpath,
                        ai_p,
                        cx,
                        cmt_ratio,
                        _rand_understanding(),
                        random.choice(["cursor", "copilot", "claude", "chatgpt"]),
                    ),
                )

        # ── file_ownership (1–3 owners per file) ───────────────────────
        for fpath in FILES:
            owners = random.sample(AUTHORS, k=random.randint(1, 3))
            for owner in owners:
                lines = random.randint(20, 300)
                last_t = now - random.randint(0, 30) * day
                conn.execute(
                    """INSERT OR IGNORE INTO file_ownership
                       (file_path, author, lines_owned, last_touched, avg_understanding)
                       VALUES (?, ?, ?, ?, ?)""",
                    (f"{DEMO_COMMIT_PREFIX}{fpath}", owner, lines, last_t, _rand_understanding()),
                )

        # ── Sprints (3) ────────────────────────────────────────────────
        sprint_scores = [82.0, 61.0, 74.0]
        for i, (name, score) in enumerate(zip(SPRINT_NAMES, sprint_scores)):
            start = now - (3 - i) * 14 * day
            end = start + 14 * day
            conn.execute(
                """INSERT INTO sprints
                   (sprint_name, start_date, end_date, total_lines_ai, total_lines_human,
                    avg_understanding, debt_delta_hours, health_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"{DEMO_COMMIT_PREFIX}{name}",
                    start,
                    end,
                    random.randint(200, 800),
                    random.randint(100, 500),
                    round(random.uniform(3.0, 4.5), 2),
                    round(random.uniform(-2.0, 5.0), 1),
                    score,
                ),
            )

        conn.commit()

    return _count_demo(db_path)


def _count_demo(db_path: Path) -> dict:
    """Return counts of demo-tagged rows."""
    out = {"commits": 0, "files": 0, "authors": 0, "sprints": 0}
    if not db_path.exists():
        return out
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM commits WHERE commit_hash LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        ).fetchone()
        out["commits"] = row[0] if row else 0

        row = conn.execute(
            "SELECT COUNT(DISTINCT author) FROM commits WHERE commit_hash LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        ).fetchone()
        out["authors"] = row[0] if row else 0

        row = conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM file_scores WHERE commit_hash LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        ).fetchone()
        out["files"] = row[0] if row else 0

        row = conn.execute(
            "SELECT COUNT(*) FROM sprints WHERE sprint_name LIKE ?",
            (f"{DEMO_COMMIT_PREFIX}%",),
        ).fetchone()
        out["sprints"] = row[0] if row else 0

    return out
