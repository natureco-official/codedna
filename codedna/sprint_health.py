"""Sprint-based code health score calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from codedna.db import get_connection, get_sprint_history, save_sprint

# Health score thresholds (0-100)
_HEALTHY_THRESHOLD = 80
_WARNING_THRESHOLD = 50

# High-risk AI threshold
_HIGH_RISK_AI = 0.7


@dataclass
class SprintResult:
    """Health analysis for a single sprint."""

    sprint_name: str
    start_date: datetime
    end_date: datetime
    health_score: float            # 0-100
    status: str                    # HEALTHY / WARNING / RISKY
    avg_understanding: Optional[float]
    ai_ratio: float                # ratio of high-risk AI files
    debt_delta_hours: float        # debt change (+ = increased, - = decreased)
    total_commits: int
    ai_lines: int
    human_lines: int

    @property
    def ai_human_ratio_str(self) -> str:
        """Return AI/human ratio as a percentage string."""
        total = self.ai_lines + self.human_lines
        if total == 0:
            return "N/A"
        ai_pct = self.ai_lines / total * 100
        return f"{ai_pct:.0f}% AI / {100-ai_pct:.0f}% Human"


def _determine_status(score: float) -> str:
    """Return status label based on score range."""
    if score >= _HEALTHY_THRESHOLD:
        return "HEALTHY"
    return "WARNING" if score >= 50 else "RISKY"


def calculate_sprint_health(
    repo_path: Path,
    db_path: Path,
    start_date: datetime,
    end_date: datetime,
    sprint_name: str = "Sprint",
) -> SprintResult:
    """
    Analyze commits in the given date range and produce a sprint health score.

    Health score formula (0-100):
      - understanding_score = (avg_understanding / 5) * 40   max 40 points
      - ai_balance          = (1 - high_risk_ai_ratio) * 30  max 30 points
      - debt_trend          = max(0, 1 - delta_ratio) * 30   max 30 points

    Args:
        repo_path: Git repo root directory
        db_path: SQLite database path
        start_date: Sprint start date
        end_date: Sprint end date
        sprint_name: Sprint name

    Returns:
        SprintResult object
    """
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    # Fetch commits and file scores in the sprint date range
    try:
        with get_connection(db_path) as conn:
            commits = conn.execute(
                """
                SELECT c.commit_hash, c.understanding_score, c.timestamp
                FROM commits c
                WHERE c.timestamp >= ? AND c.timestamp <= ?
                ORDER BY c.timestamp ASC
                """,
                (start_ts, end_ts),
            ).fetchall()
    except Exception:
        commits = []

    total_commits = len(commits)

    # Collect file scores
    ai_scores: list[float] = []
    understanding_scores: list[float] = []

    try:
        with get_connection(db_path) as conn:
            for commit in commits:
                files = conn.execute(
                    """
                    SELECT ai_probability, understanding_score
                    FROM file_scores
                    WHERE commit_hash = ?
                    """,
                    (commit["commit_hash"],),
                ).fetchall()
                for f in files:
                    if f["ai_probability"] is not None:
                        ai_scores.append(float(f["ai_probability"]))
                    if f["understanding_score"] is not None:
                        understanding_scores.append(float(f["understanding_score"]))
    except Exception:
        pass

    # Average understanding score
    avg_understanding = (
        sum(understanding_scores) / len(understanding_scores)
        if understanding_scores else None
    )

    # High-risk AI ratio (>= 0.7)
    high_risk_count = sum(1 for a in ai_scores if a >= _HIGH_RISK_AI)
    ai_ratio = high_risk_count / len(ai_scores) if ai_scores else 0.0

    # AI / human line estimate (AI score > 0.5 → counted as AI line)
    ai_lines = sum(1 for a in ai_scores if a > 0.5) * 50  # approximate
    human_lines = max(len(ai_scores) * 50 - ai_lines, 0)

    # Technical debt delta — calculate full repo debt (no sprint start/end diff,
    # use current state as baseline, negative = debt decreased)
    from codedna.tech_debt import calculate_repo_debt
    try:
        summary = calculate_repo_debt(repo_path, db_path)
        debt_delta = summary.total_debt_hours / max(total_commits, 1)
    except Exception:
        debt_delta = 0.0

    # ---- Calculate health score ----
    # 1. Understanding score (max 40)
    understanding_points = ((avg_understanding / 5.0) * 40.0) if avg_understanding is not None else 20.0

    # 2. AI balance score (max 30)
    ai_balance = (1.0 - ai_ratio) * 30.0

    # 3. Debt trend score (max 30) — lower debt_delta is better
    delta_ratio = min(debt_delta / 10.0, 1.0)   # normalize to 10 hours
    debt_trend = max(0.0, 1.0 - delta_ratio) * 30.0

    health_score = round(understanding_points + ai_balance + debt_trend, 1)
    status = _determine_status(health_score)

    return SprintResult(
        sprint_name=sprint_name,
        start_date=start_date,
        end_date=end_date,
        health_score=health_score,
        status=status,
        avg_understanding=round(avg_understanding, 2) if avg_understanding is not None else None,
        ai_ratio=round(ai_ratio, 3),
        debt_delta_hours=round(debt_delta, 2),
        total_commits=total_commits,
        ai_lines=ai_lines,
        human_lines=human_lines,
    )


def save_sprint_result(result: SprintResult, db_path: Path) -> int:
    """Save sprint result to DB and return new id."""
    return save_sprint(
        sprint_name=result.sprint_name,
        start_date=int(result.start_date.timestamp()),
        end_date=int(result.end_date.timestamp()),
        total_lines_ai=result.ai_lines,
        total_lines_human=result.human_lines,
        avg_understanding=result.avg_understanding,
        debt_delta_hours=result.debt_delta_hours,
        health_score=result.health_score,
        db_path=db_path,
    )
