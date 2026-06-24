"""Converts technical debt to a monetary value."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection, get_file_scores_for_commit, get_commit_history

# Default hourly rate (USD)
_DEFAULT_HOURLY_RATE = 75.0

# Risk thresholds (monthly cost)
_CRITICAL_THRESHOLD = 100.0   # $/month and above → CRITICAL
_HIGH_THRESHOLD     = 50.0    # $/month and above → HIGH


@dataclass
class FileDebt:
    """Technical debt analysis for a single file."""

    file_path: str             # kept for API compatibility (was: dosya_yolu)
    debt_hours: float        # estimated debt hours (kept for compat; was: debt_saatleri)
    monthly_cost_usd: float    # amortized monthly cost (kept for compat; was: aylik_maliyet_usd)
    risk_level: str          # CRITICAL / HIGH / MEDIUM / LOW (kept for compat; was: risk_seviyesi)
    total_lines: int
    ai_probability: float
    complexity: float
    understanding_score: Optional[float]


@dataclass
class RepoDebt:
    """Repo-wide technical debt summary."""

    total_debt_hours: float      # kept for API compatibility (was: toplam_debt_saatleri)
    total_monthly_cost_usd: float  # kept for API compatibility (was: toplam_aylik_maliyet_usd)
    top_5_most_expensive: list[FileDebt]      # kept for API compatibility (was: en_pahali_5)
    total_files: int
    hourly_rate: float


def _calculate_risk(monthly_cost: float) -> str:
    """Return risk level based on monthly cost."""
    if monthly_cost >= _CRITICAL_THRESHOLD:
        return "CRITICAL"
    elif monthly_cost >= _HIGH_THRESHOLD:
        return "HIGH"
    elif monthly_cost >= 20.0:
        return "MEDIUM"
    return "LOW"


def _calculate_debt_hours(
    understanding_score: Optional[float],
    ai_probability: float,
    complexity: float,
    total_lines: int,
) -> float:
    """
    Calculate technical debt hours for a file.

    Formula:
        debt_hours = (
            (1 - understanding_score/5) * 0.4   ← low understanding
          + ai_probability * 0.35                ← AI code
          + min(complexity/20, 1.0) * 0.25       ← complexity
        ) * (lines_of_code / 100) * 2

    Defaults to 2.5/5 if no understanding score is available.
    """
    understanding = understanding_score if understanding_score is not None else 2.5
    understanding_factor = (1.0 - understanding / 5.0) * 0.40
    ai_factor = ai_probability * 0.35
    complexity_factor = min(complexity / 20.0, 1.0) * 0.25

    line_multiplier = (total_lines / 100.0) * 2.0

    return (understanding_factor + ai_factor + complexity_factor) * line_multiplier


def calculate_file_debt(
    file_path: str,
    db_path: Path,
    hourly_rate: float = _DEFAULT_HOURLY_RATE,
) -> Optional[FileDebt]:
    """
    Calculate debt hours and dollar cost for a single file.
    Looks up the DB first; falls back to direct file analysis if not found.

    Args:
        file_path: File path (absolute or relative)
        db_path: SQLite database path
        hourly_rate: Hourly rate ($/hour)

    Returns:
        FileDebt object, or None if the file is not found
    """
    # Try to find the most recent score from DB first
    row = None
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT fs.ai_probability, fs.complexity_score, fs.understanding_score
                FROM file_scores fs
                JOIN commits c ON fs.commit_hash = c.commit_hash
                WHERE fs.file_path = ?
                ORDER BY c.timestamp DESC
                LIMIT 1
                """,
                (file_path,),
            ).fetchone()
    except Exception:
        pass

    # Use DB values or analyze the file directly
    if row:
        ai = float(row["ai_probability"] or 0.0)
        complexity = float(row["complexity_score"] or 1.0)
        understanding = float(row["understanding_score"]) if row["understanding_score"] is not None else None
    else:
        # Not in DB — analyze directly with tree-sitter
        p = Path(file_path)
        if not p.exists():
            return None
        try:
            from codedna.analyzer import analyze_file
            result = analyze_file(p)
            if result.desteklenmiyor or result.hata:
                return None
            ai = result.ai_probability
            complexity = result.complexity_score
            understanding = None
        except Exception:
            return None

    # Line count
    total_lines = 100
    try:
        p = Path(file_path)
        if p.exists():
            total_lines = len(p.read_text(errors="replace").splitlines())
    except Exception:
        pass

    debt_hours = _calculate_debt_hours(understanding, ai, complexity, total_lines)
    monthly_cost = debt_hours * hourly_rate / 12.0

    return FileDebt(
        file_path=file_path,
        debt_hours=round(debt_hours, 2),
        monthly_cost_usd=round(monthly_cost, 2),
        risk_level=_calculate_risk(monthly_cost),
        total_lines=total_lines,
        ai_probability=round(ai, 3),
        complexity=round(complexity, 1),
        understanding_score=round(understanding, 2) if understanding is not None else None,
    )


def calculate_repo_debt(
    repo_path: Path,
    db_path: Path,
    hourly_rate: float = _DEFAULT_HOURLY_RATE,
) -> RepoDebt:
    """
    Calculate the total technical debt summary for the repo.

    Args:
        repo_path: Git repo root directory
        db_path: SQLite database path
        hourly_rate: Hourly rate ($/hour)

    Returns:
        RepoDebt summary object
    """
    # Scan repo files — scan_repository only returns git-tracked files
    # (.gitignore entries excluded). We do NOT use DB paths as the source:
    # stale records (build artifacts, etc.) must not be counted.
    from codedna.scorer import scan_repository
    scanned = scan_repository(repo_path, max_files=200)
    scan_paths = {s.file_path for s in scanned}

    # Use DB understanding scores only to enrich — not to determine the file list
    all_paths = list(scan_paths)

    file_debts: list[FileDebt] = []
    for path in all_paths:
        # Use DB if available, otherwise calculate from scan results
        debt = calculate_file_debt(path, db_path, hourly_rate)
        if debt is None:
            # Fall back to scanned result
            scanned_result = next((s for s in scanned if s.file_path == path), None)
            if scanned_result:
                debt_hours = _calculate_debt_hours(
                    None,
                    scanned_result.ai_probability,
                    scanned_result.complexity_score,
                    scanned_result.total_lines,
                )
                monthly = debt_hours * hourly_rate / 12.0
                debt = FileDebt(
                    file_path=path,
                    debt_hours=round(debt_hours, 2),
                    monthly_cost_usd=round(monthly, 2),
                    risk_level=_calculate_risk(monthly),
                    total_lines=scanned_result.total_lines,
                    ai_probability=round(scanned_result.ai_probability, 3),
                    complexity=round(scanned_result.complexity_score, 1),
                    understanding_score=None,
                )
        if debt:
            file_debts.append(debt)

    # Top 5 most expensive files
    file_debts.sort(key=lambda d: d.monthly_cost_usd, reverse=True)
    top_5 = file_debts[:5]

    total_hours = sum(d.debt_hours for d in file_debts)
    total_monthly = sum(d.monthly_cost_usd for d in file_debts)

    return RepoDebt(
        total_debt_hours=round(total_hours, 2),
        total_monthly_cost_usd=round(total_monthly, 2),
        top_5_most_expensive=top_5,
        total_files=len(file_debts),
        hourly_rate=hourly_rate,
    )
