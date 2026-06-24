"""Measures the productivity ramp-up curve of new developers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from codedna.db import get_connection

# Productivity threshold — crossing this score means "ramp-up complete"
_DEFAULT_THRESHOLD = 3.5

# Minimum number of commits required for ramp-up estimation
_MIN_COMMITS = 5


@dataclass
class CommitDataPoint:
    """Understanding score data for a single commit."""

    commit_hash: str
    commit_no: int           # author-relative sequence number (starts at 1)
    date: datetime          # kept for API/chart compatibility (was: tarih)
    understanding_score: Optional[float]
    week_number: int            # weeks elapsed since first commit (for chart compat; was: hafta_no)


@dataclass
class AuthorCurve:
    """Onboarding curve for a single author."""

    author: str               # kept for API compatibility (was: yazar)
    total_commits: int
    commits_with_understanding: int
    ramp_up_weeks: Optional[float]   # None = insufficient data / threshold not reached (was: ramp_up_hafta)
    latest_avg_understanding: Optional[float]  # average of last 5 commits (was: son_ort_anlama)
    points: list[CommitDataPoint]


def get_author_timeline(author: str, db_path: Path) -> list[CommitDataPoint]:
    """
    Return all commits for an author in chronological order with understanding scores.

    Args:
        author: Author name (must match commits.author)
        db_path: SQLite database path

    Returns:
        List of CommitDataPoint sorted by date
    """
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT commit_hash, author, timestamp, understanding_score
                FROM commits
                WHERE author = ?
                ORDER BY timestamp ASC
                """,
                (author,),
            ).fetchall()
    except Exception:
        return []

    if not rows:
        return []

    first_ts = rows[0]["timestamp"] or 0
    points: list[CommitDataPoint] = []

    for i, r in enumerate(rows):
        ts = r["timestamp"] or first_ts
        week = int((ts - first_ts) / (7 * 24 * 3600))
        points.append(
            CommitDataPoint(
                commit_hash=r["commit_hash"] or "",
                commit_no=i + 1,
                date=datetime.fromtimestamp(ts),
                understanding_score=(
                    float(r["understanding_score"])
                    if r["understanding_score"] is not None
                    else None
                ),
                week_number=week,
            )
        )

    return points


def estimate_ramp_up_weeks(
    author: str,
    db_path: Path,
    threshold: float = _DEFAULT_THRESHOLD,
) -> Optional[float]:
    """
    Estimate the first week when the author's average understanding score exceeds the threshold.

    Algorithm:
      - Commits with understanding scores are smoothed with a 3-point moving average
      - Returns the week number of the first commit where the smoothed score exceeds the threshold
      - Returns None if insufficient data (< MIN_COMMITS surveyed commits)

    Args:
        author: Author name
        db_path: SQLite database path
        threshold: Productivity threshold (default 3.5/5)

    Returns:
        Ramp-up week number, or None
    """
    points = get_author_timeline(author, db_path)
    surveyed = [p for p in points if p.understanding_score is not None]

    if len(surveyed) < _MIN_COMMITS:
        return None

    # 3-point moving average
    scores = [p.understanding_score for p in surveyed]  # type: ignore[misc]
    for i in range(2, len(scores)):
        window = scores[max(0, i - 2): i + 1]
        avg = sum(window) / len(window)
        if avg >= threshold:
            return float(surveyed[i].week_number)

    return None  # threshold never reached


def get_author_curve(author: str, db_path: Path) -> AuthorCurve:
    """
    Build a complete onboarding curve object for a single author.

    Args:
        author: Author name
        db_path: SQLite database path

    Returns:
        AuthorCurve object
    """
    points = get_author_timeline(author, db_path)
    surveyed = [p for p in points if p.understanding_score is not None]

    ramp_up = estimate_ramp_up_weeks(author, db_path)

    last_5 = [p.understanding_score for p in surveyed[-5:] if p.understanding_score]
    latest_avg = sum(last_5) / len(last_5) if last_5 else None

    return AuthorCurve(
        author=author,
        total_commits=len(points),
        commits_with_understanding=len(surveyed),
        ramp_up_weeks=round(ramp_up, 1) if ramp_up is not None else None,
        latest_avg_understanding=round(latest_avg, 2) if latest_avg is not None else None,
        points=points,
    )


def get_all_authors(db_path: Path) -> list[str]:
    """Return all unique authors in the DB."""
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT author FROM commits WHERE author IS NOT NULL ORDER BY author"
            ).fetchall()
        return [r["author"] for r in rows]
    except Exception:
        return []


def team_onboarding_summary(db_path: Path) -> list[dict]:
    """
    Return a ramp-up summary for all authors on the team.

    Returns:
        List of per-author summary dicts, sorted by ramp_up_weeks
    """
    authors = get_all_authors(db_path)
    summary: list[dict] = []

    for author in authors:
        curve = get_author_curve(author, db_path)
        summary.append({
            "author": author,
            "total_commits": curve.total_commits,
            "commits_with_understanding": curve.commits_with_understanding,
            "ramp_up_weeks": curve.ramp_up_weeks,
            "latest_avg_understanding": curve.latest_avg_understanding,
            "sufficient_data": curve.commits_with_understanding >= _MIN_COMMITS,
        })

    # Sort: authors with ramp-up data first, then None
    summary.sort(key=lambda x: (x["ramp_up_weeks"] is None, x["ramp_up_weeks"] or 999))
    return summary
