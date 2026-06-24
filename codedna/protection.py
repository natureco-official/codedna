"""Understanding threshold monitoring for critical modules — code ownership insurance."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection

# Status constants
_STATUS_VIOLATION = "VIOLATION"
_STATUS_SAFE      = "SAFE"
_STATUS_UNKNOWN   = "UNKNOWN"

# Minimum time between warnings for the same module (anti-spam, seconds)
_MIN_ALERT_INTERVAL = 3600  # 1 hour


@dataclass
class ModuleStatus:
    """Current status of a single protected module."""

    file_path: str     # kept for API compatibility (was: dosya_yolu)
    label: str         # kept for API compatibility (was: etiket)
    threshold: float    # kept for API compatibility (was: esik)
    current_score: Optional[float]  # kept for API compatibility (was: mevcut_skor)
    status: str          # VIOLATION / SAFE / UNKNOWN
    active: bool


def protect_module(
    file_path: str,
    threshold: float,
    label: str,
    author: str,
    db_path: Path,
) -> int:
    """
    Mark a file as a protected module.

    Args:
        file_path: Path of the file to protect
        threshold: Minimum understanding score threshold (1.0–5.0)
        label: Human-readable label (e.g. "Payment System")
        author: Who added the protection
        db_path: SQLite database path

    Returns:
        New record id
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO protected_modules
                (file_path, min_understanding_threshold, label, added_by, added_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(file_path) DO UPDATE SET
                min_understanding_threshold = excluded.min_understanding_threshold,
                label     = excluded.label,
                added_by  = excluded.added_by,
                added_at  = excluded.added_at,
                is_active = 1
            """,
            (file_path, threshold, label, author, int(time.time())),
        )
        return cur.lastrowid or 0


def unprotect_module(file_path: str, db_path: Path) -> bool:
    """
    Remove protection (set is_active = 0, do not delete the record).

    Args:
        file_path: Path of the file to unprotect
        db_path: SQLite database path

    Returns:
        True if a record was found and updated
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE protected_modules SET is_active = 0 WHERE file_path = ?",
            (file_path,),
        )
        return cur.rowcount > 0


def _get_current_score(file_path: str, db_path: Path) -> Optional[float]:
    """Fetch the most recent understanding score for a file from the DB."""
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT fs.understanding_score
                FROM file_scores fs
                JOIN commits c ON fs.commit_hash = c.commit_hash
                WHERE fs.file_path = ? AND fs.understanding_score IS NOT NULL
                ORDER BY c.timestamp DESC
                LIMIT 1
                """,
                (file_path,),
            ).fetchone()
        return float(row["understanding_score"]) if row else None
    except Exception:
        return None


def check_protected_modules(db_path: Path) -> list[ModuleStatus]:
    """
    Check all active protected modules and determine whether they meet their threshold.

    Returns:
        List of ModuleStatus
    """
    try:
        with get_connection(db_path) as conn:
            records = conn.execute(
                """
                SELECT file_path, min_understanding_threshold, label, is_active
                FROM protected_modules
                WHERE is_active = 1
                ORDER BY label
                """
            ).fetchall()
    except Exception:
        return []

    results: list[ModuleStatus] = []
    for r in records:
        current = _get_current_score(r["file_path"], db_path)

        if current is None:
            status = _STATUS_UNKNOWN
        elif current >= r["min_understanding_threshold"]:
            status = _STATUS_SAFE
        else:
            status = _STATUS_VIOLATION

        results.append(
            ModuleStatus(
                file_path=r["file_path"],
                label=r["label"] or r["file_path"],
                threshold=r["min_understanding_threshold"],
                current_score=round(current, 2) if current is not None else None,
                status=status,
                active=bool(r["is_active"]),
            )
        )

    return results


def get_violations(db_path: Path) -> list[ModuleStatus]:
    """
    Return only modules that have fallen below their threshold (VIOLATION status).

    Returns:
        List of ModuleStatus in violation
    """
    return [m for m in check_protected_modules(db_path) if m.status == _STATUS_VIOLATION]


def show_violation_warnings(db_path: Path) -> list[str]:
    """
    Return violation warnings for the post-commit hook.
    Skips modules that were already warned about within the last hour (anti-spam).

    Returns:
        List of warning messages (empty = no violations)
    """
    violations = get_violations(db_path)
    if not violations:
        return []

    now = int(time.time())
    warnings: list[str] = []

    for v in violations:
        # Check last alert time
        try:
            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT last_alert_at FROM protected_modules WHERE file_path = ?",
                    (v.file_path,),
                ).fetchone()
            last_alert = row["last_alert_at"] if row and row["last_alert_at"] else 0
        except Exception:
            last_alert = 0

        if now - last_alert < _MIN_ALERT_INTERVAL:
            continue

        # Update alert time
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    "UPDATE protected_modules SET last_alert_at = ? WHERE file_path = ?",
                    (now, v.file_path),
                )
        except Exception:
            pass

        score_str = f"{v.current_score:.1f}" if v.current_score else "?"
        warnings.append(
            f"⚠️  WARNING: {v.file_path} can no longer be safely modified "
            f"(understanding: {score_str} < threshold: {v.threshold:.1f})"
        )

    return warnings
