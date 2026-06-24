"""Bus factor calculation — how many people truly understand each file."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from codedna.db import get_file_ownership, upsert_file_ownership

# Large-repo warning threshold
_LARGE_REPO_THRESHOLD = 500

# Sufficient understanding threshold (authors below this are not counted as "knowledgeable")
_UNDERSTANDING_THRESHOLD = 3.5

# Minimum line ownership percentage to be counted as a primary owner
_OWNERSHIP_THRESHOLD = 0.10  # 10% → considered "involved" in the file


@dataclass
class FileOwnership:
    """Author-based ownership summary for a single file."""

    file_path: str       # kept for API compatibility (was: dosya_yolu)
    total_lines: int     # kept for API compatibility (was: toplam_satir)
    authors: dict[str, int] = field(default_factory=dict)  # author → line count

    @property
    def primary_owner(self) -> Optional[str]:
        """Return the author with the most lines."""
        if not self.authors:
            return None
        return max(self.authors, key=lambda a: self.authors[a])

    @property
    def primary_ownership_percentage(self) -> float:
        """Primary owner's ownership percentage (0.0–1.0)."""
        if not self.authors or self.total_lines == 0:
            return 0.0
        primary = self.primary_owner
        return self.authors.get(primary or "", 0) / self.total_lines


@dataclass
class BusFactorResult:
    """Bus factor result for a single file."""

    file_path: str           # kept for API compatibility (was: dosya_yolu)
    bus_factor: int           # how many people understand this file
    primary_owner: Optional[str]
    ownership_percentage: float   # primary owner's percentage (was: sahiplik_yuzdesi)
    risk: str                 # CRITICAL / RISKY / SAFE
    knowledgeable_authors: list[str]   # authors with understanding_score >= threshold (was: anlayan_yazarlar)
    total_lines: int


def _run_git_blame(file_path: Path, repo_root: Path) -> dict[str, int]:
    """
    Perform per-line author detection using git blame --line-porcelain.

    Returns:
        {author_name: line_count} dict
    """
    try:
        relative = file_path.relative_to(repo_root)
    except ValueError:
        relative = file_path

    try:
        result = subprocess.run(
            ["git", "blame", "--line-porcelain", str(relative)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    if result.returncode != 0:
        return {}

    # Collect "author " lines from output
    author_lines: dict[str, int] = defaultdict(int)
    for line in result.stdout.splitlines():
        if line.startswith("author "):
            author = line[7:].strip()
            # Skip the special "Not Committed Yet" entry
            if author and author != "Not Committed Yet":
                author_lines[author] += 1

    return dict(author_lines)


def _list_tracked_files(repo_root: Path, max_files: int = _LARGE_REPO_THRESHOLD) -> list[Path]:
    """
    List supported source files tracked by Git.

    Args:
        repo_root: Git repo root directory
        max_files: Maximum number of files to process (for performance)

    Returns:
        List of absolute Paths
    """
    supported = {".py", ".js", ".jsx", ".ts", ".tsx"}

    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        files = result.stdout.strip().splitlines()
    except Exception:
        files = []

    filtered = [
        repo_root / f for f in files
        if Path(f).suffix.lower() in supported and (repo_root / f).exists()
    ]
    return filtered[:max_files]


def calculate_bus_factor(
    repo_path: Path,
    db_path: Path,
    max_files: int = _LARGE_REPO_THRESHOLD,
) -> list[BusFactorResult]:
    """
    Calculate the bus factor for every file in the repo and save to DB.

    Bus factor = number of authors who own >50% of the file
    AND have understanding_score >= 3.5.
    When no understanding score is available, ownership >= 10% is sufficient.

    Args:
        repo_path: Git repo root directory
        max_files: Maximum number of files to process

    Returns:
        List of BusFactorResult sorted by bus_factor ascending
    """
    root = Path(repo_path).resolve()
    files = _list_tracked_files(root, max_files)

    # Fetch current understanding scores from DB in a single query
    from codedna.db import get_connection
    understanding_map: dict[tuple[str, str], float] = {}  # (file_path, author) → score
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT fo.file_path, fo.author, fo.avg_understanding
                FROM file_ownership fo
                WHERE fo.avg_understanding IS NOT NULL
                """
            ).fetchall()
            for r in rows:
                understanding_map[(r["file_path"], r["author"])] = float(r["avg_understanding"])
    except Exception:
        pass

    results: list[BusFactorResult] = []

    for file in files:
        author_lines = _run_git_blame(file, root)
        if not author_lines:
            continue

        total = sum(author_lines.values())
        if total == 0:
            continue

        # Save to DB
        for author, lines in author_lines.items():
            understanding = understanding_map.get((str(file), author))
            upsert_file_ownership(
                file_path=str(file),
                author=author,
                lines_owned=lines,
                last_touched=0,
                avg_understanding=understanding,
                db_path=db_path,
            )

        # Identify "knowledgeable" authors
        knowledgeable: list[str] = []
        for author, lines in author_lines.items():
            pct = lines / total
            score = understanding_map.get((str(file), author))
            if score is not None:
                if score >= _UNDERSTANDING_THRESHOLD and pct >= _OWNERSHIP_THRESHOLD:
                    knowledgeable.append(author)
            elif pct >= _OWNERSHIP_THRESHOLD:
                # No survey data — fall back to ownership percentage
                knowledgeable.append(author)

        bus_factor = max(len(knowledgeable), 1)
        if bus_factor == 1:
            risk = "CRITICAL"
        elif bus_factor == 2:
            risk = "RISKY"
        else:
            risk = "SAFE"

        # Primary owner
        primary = max(author_lines, key=lambda a: author_lines[a])
        primary_pct = author_lines[primary] / total

        # Relative file path
        try:
            relative_path = str(file.relative_to(root))
        except ValueError:
            relative_path = str(file)

        results.append(
            BusFactorResult(
                file_path=relative_path,
                bus_factor=bus_factor,
                primary_owner=primary,
                ownership_percentage=round(primary_pct * 100, 1),
                risk=risk,
                knowledgeable_authors=knowledgeable,
                total_lines=total,
            )
        )

    # Sort ascending by bus_factor (CRITICAL first)
    results.sort(key=lambda s: s.bus_factor)
    return results


def get_at_risk_files(
    repo_path: Path,
    db_path: Path,
) -> list[BusFactorResult]:
    """
    Return files where bus_factor == 1 (CRITICAL list).

    Args:
        repo_path: Git repo root directory
        db_path: SQLite database path

    Returns:
        List of BusFactorResult for critical files
    """
    all_results = calculate_bus_factor(repo_path, db_path)
    return [s for s in all_results if s.bus_factor == 1]
