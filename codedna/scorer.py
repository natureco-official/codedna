"""Calculate single_commit_ratio from git history and score commits."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from git import InvalidGitRepositoryError, Repo
from rich.console import Console

from codedna.analyzer import FileAnalysisResult, analyze_file

console = Console()


def get_repo(path: Optional[Path] = None) -> Optional[Repo]:
    """Return the Git repo object, or None if not found."""
    try:
        return Repo(path or Path.cwd(), search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None


def calculate_single_commit_ratio(repo: Repo, file_path: str) -> float:
    """
    Calculate what fraction of a file's lines were added in a single commit.

    Strategy: Return the ratio of the largest single-commit contribution
    to the total lines across the file's commit history.

    Args:
        repo: Git repo object
        file_path: File path relative to the repo root

    Returns:
        Ratio between 0.0 and 1.0
    """
    try:
        # Fetch the commit history for this file
        commits = list(repo.iter_commits(paths=file_path, max_count=50))
        if not commits:
            return 0.0

        # Collect the number of inserted lines per commit
        commit_contributions: list[int] = []
        for commit in commits:
            try:
                if commit.parents:
                    diff = commit.parents[0].diff(commit, paths=[file_path])
                else:
                    # First commit
                    diff = commit.diff(None, paths=[file_path])

                for d in diff:
                    if d.a_blob or d.b_blob:
                        # Estimate inserted line count
                        try:
                            stats = commit.stats.files.get(file_path, {})
                            inserted = stats.get("insertions", 0)
                            commit_contributions.append(inserted)
                        except Exception:
                            pass
            except Exception:
                pass

        if not commit_contributions:
            # Fallback: count as 100% if there is only one commit
            return 1.0 if len(commits) == 1 else 0.5

        total = sum(commit_contributions)
        if total == 0:
            return 0.0

        largest = max(commit_contributions)
        return min(largest / total, 1.0)

    except Exception as exc:
        console.log(f"[dim]single_commit_ratio error for {file_path}: {exc}[/dim]")
        return 0.0


def scan_repository(
    repo_path: Optional[Path] = None,
    max_files: int = 200,
) -> list[FileAnalysisResult]:
    """
    Scan all supported files in the repo.

    Important: When a Git repo is present, ONLY git-tracked files are scanned.
    This automatically excludes build artifacts in .gitignore (`.next/`, `out/`,
    `node_modules/`, etc.).
    Without a Git repo (directory not yet `git init`-ed), falls back to the
    old behavior — directory-based filtering is applied.

    Args:
        repo_path: Repo root directory (defaults to current directory)
        max_files: Maximum number of files to scan

    Returns:
        List of FileAnalysisResult
    """
    root = Path(repo_path or Path.cwd()).resolve()
    repo = get_repo(root)

    supported_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}

    # Directory blocklist — for non-git repos + extra safety layer
    skipped_dirs = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".mypy_cache", ".pytest_cache",
        ".next",         # Next.js build output
        "out",           # Next.js static export / tsc output
        ".turbo",        # Turborepo cache
        ".parcel-cache",
        "coverage",
        ".nyc_output",
    }

    # Git-tracked files — this list is the primary filter
    tracked_files: set[str] = set()
    if repo:
        try:
            tracked_files = {item for item in repo.git.ls_files().splitlines()}
        except Exception:
            pass

    results: list[FileAnalysisResult] = []
    count = 0

    for file in root.rglob("*"):
        if count >= max_files:
            break

        # Skip blocklisted directories (also works for non-git repos)
        parts = file.parts
        if any(skip in parts for skip in skipped_dirs):
            continue

        if not file.is_file():
            continue

        if file.suffix.lower() not in supported_extensions:
            continue

        relative_path = str(file.relative_to(root))

        # Key fix: when a Git repo is present, scan ONLY git-tracked files.
        # This automatically excludes all build/generated files in .gitignore.
        # Without git, skip this filter — the directory blocklist provides enough protection.
        if repo and tracked_files and relative_path not in tracked_files:
            continue

        # Calculate single_commit_ratio (when git is tracking)
        single_commit_ratio = 0.0
        if repo and relative_path in tracked_files:
            single_commit_ratio = calculate_single_commit_ratio(repo, relative_path)

        result = analyze_file(file, single_commit_ratio=single_commit_ratio)
        if not result.unsupported and result.error is None:
            results.append(result)
            count += 1

    return results


def get_commit_files(repo: Repo, commit_hash: Optional[str] = None) -> list[str]:
    """
    List files changed in a specific commit (or HEAD).

    Args:
        repo: Git repo object
        commit_hash: Commit hash to inspect (defaults to HEAD)

    Returns:
        List of changed file paths
    """
    try:
        if commit_hash:
            commit = repo.commit(commit_hash)
        else:
            commit = repo.head.commit

        return list(commit.stats.files.keys())
    except Exception:
        return []


def score_latest_commit(repo_path: Optional[Path] = None) -> tuple[Optional[str], list[FileAnalysisResult]]:
    """
    Analyze files in the latest commit.

    Returns:
        (commit_hash, result_list) tuple
    """
    root = Path(repo_path or Path.cwd()).resolve()
    repo = get_repo(root)
    if not repo:
        return None, []

    try:
        commit = repo.head.commit
        commit_hash = commit.hexsha
        files = get_commit_files(repo, commit_hash)
    except Exception:
        return None, []

    results: list[FileAnalysisResult] = []
    supported_extensions = {".py", ".js", ".jsx", ".ts", ".tsx"}

    for file_path in files:
        full_path = root / file_path
        if not full_path.exists():
            continue
        if full_path.suffix.lower() not in supported_extensions:
            continue

        single_commit_ratio = calculate_single_commit_ratio(repo, file_path)
        result = analyze_file(full_path, single_commit_ratio=single_commit_ratio)
        if not result.unsupported and result.error is None:
            results.append(result)

    return commit_hash, results
