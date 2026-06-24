"""Automatically posts CodeDNA analysis comments on GitHub PRs."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

# GitHub API base URL
_GH_API = "https://api.github.com"

# Hidden marker used in comments — to locate existing CodeDNA comments
_COMMENT_MARKER = "<!-- codedna-bot-comment -->"

# Security: token is never logged or included in error messages
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"


# ---------------------------------------------------------------------------
# Comment formatting
# ---------------------------------------------------------------------------

def format_pr_comment(
    scan_results: list,
    debt_summary: Optional[dict] = None,
) -> str:
    """
    Convert analysis results into a GitHub Markdown comment.

    Kept under 2000 characters for readability.
    Includes a technical debt disclaimer.

    Args:
        scan_results: List of FileAnalysisResult objects
        debt_summary: Repo debt summary dict (optional)

    Returns:
        Comment text in Markdown format
    """
    if not scan_results:
        return f"{_COMMENT_MARKER}\n## 🧬 CodeDNA Analysis\n\nNo changed files found.\n"

    total = len(scan_results)
    avg_ai = sum(s.ai_probability for s in scan_results) / total
    high_risk = [s for s in scan_results if s.ai_probability >= 0.7]

    # Risk level
    if avg_ai >= 0.7:
        risk_emoji = "🔴"
        risk_label = "HIGH"
    elif avg_ai >= 0.4:
        risk_emoji = "🟡"
        risk_label = "MEDIUM"
    else:
        risk_emoji = "🟢"
        risk_label = "LOW"

    lines = [
        _COMMENT_MARKER,
        "## 🧬 CodeDNA Analysis",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Files analyzed | {total} |",
        f"| Avg. AI probability | {avg_ai * 100:.0f}% |",
        f"| Risk level | {risk_emoji} {risk_label} |",
        f"| High-risk files (≥70%) | {len(high_risk)} |",
        "",
    ]

    # Top 3 riskiest files
    top_risky = sorted(scan_results, key=lambda s: s.ai_probability, reverse=True)[:3]
    if top_risky:
        lines.append("### ⚠️ Files Requiring Attention")
        lines.append("")
        lines.append("| File | AI Probability | Complexity |")
        lines.append("|------|---------------|------------|")
        for s in top_risky:
            try:
                from pathlib import Path
                short_path = "/".join(Path(s.file_path).parts[-2:])
            except Exception:
                short_path = s.file_path[-40:]
            lines.append(
                f"| `{short_path}` | {s.ai_probability * 100:.0f}% | {s.complexity_label} |"
            )
        lines.append("")

    # Technical debt (if available)
    if debt_summary:
        total_hours = debt_summary.get("total_debt_hours", 0) or debt_summary.get("toplam_debt_saatleri", 0)
        lines.append("### 💰 Technical Debt Estimate")
        lines.append("")
        lines.append(f"Estimated debt: **{total_hours:.1f} hours**")
        lines.append("")
        lines.append(
            "> ℹ️ *This is an estimation model based on understanding score, AI probability, "
            "and complexity weights. It is not precise accounting data.*"
        )
        lines.append("")

    # Footer
    lines += [
        "---",
        "<sub>🧬 [CodeDNA](https://github.com/codedna/codedna) · "
        "Run `codedna dashboard` for detailed analysis.</sub>",
    ]

    comment = "\n".join(lines)

    # Truncate if over 2000 characters
    if len(comment) > 2000:
        summary = "\n".join(lines[:20])
        comment = (
            summary + "\n\n"
            "*... (truncated — see CodeDNA dashboard for full report)*\n\n"
            f"---\n<sub>🧬 CodeDNA</sub>\n{_COMMENT_MARKER}"
        )

    return comment


# ---------------------------------------------------------------------------
# GitHub API operations
# ---------------------------------------------------------------------------

def _gh_request(
    method: str,
    url: str,
    token: str,
    data: Optional[dict] = None,
) -> dict:
    """
    Send an authenticated request to the GitHub API.

    Security: token is only used in the Authorization header,
    never logged or added to error messages.
    """
    body = json.dumps(data).encode("utf-8") if data else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        body_str = e.read().decode("utf-8", errors="replace")
        # NEVER include the token in error messages
        raise RuntimeError(f"GitHub API error ({e.code}): {body_str[:300]}")


def find_existing_comment(
    repo: str,
    pr_number: int,
    token: str,
) -> Optional[int]:
    """
    Find the ID of an existing CodeDNA bot comment (by marker).

    Args:
        repo: Repo name in "owner/repo" format
        pr_number: PR number
        token: GitHub token

    Returns:
        Comment ID, or None if not found
    """
    url = f"{_GH_API}/repos/{repo}/issues/{pr_number}/comments?per_page=100"
    try:
        comments = _gh_request("GET", url, token)
    except Exception:
        return None

    if not isinstance(comments, list):
        return None

    for comment in comments:
        body = comment.get("body", "")
        if _COMMENT_MARKER in body:
            return comment.get("id")

    return None


def post_or_update_comment(
    repo: str,
    pr_number: int,
    body: str,
    token: str,
) -> dict:
    """
    Post a CodeDNA comment on a PR or update the existing one.

    Anti-spam: a new comment is not created on every push — the existing
    CodeDNA comment is found and updated via PATCH. If none exists, POST.

    Args:
        repo: Repo name in "owner/repo" format
        pr_number: PR number
        body: Comment text (Markdown)
        token: GitHub token

    Returns:
        GitHub API response
    """
    existing_id = find_existing_comment(repo, pr_number, token)

    if existing_id:
        # Update existing comment — no spam
        url = f"{_GH_API}/repos/{repo}/issues/comments/{existing_id}"
        return _gh_request("PATCH", url, token, {"body": body})
    else:
        # Post first comment
        url = f"{_GH_API}/repos/{repo}/issues/{pr_number}/comments"
        return _gh_request("POST", url, token, {"body": body})


# ---------------------------------------------------------------------------
# Auto-detect PR info from GitHub Actions environment
# ---------------------------------------------------------------------------

def github_actions_pr_bilgisi() -> Optional[tuple[str, int]]:
    """
    Auto-detect the repo name and PR number from the GitHub Actions environment.

    Uses the GITHUB_REPOSITORY and GITHUB_EVENT_PATH environment variables.

    Returns:
        (repo, pr_number) tuple, or None if not detectable
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not repo or not event_path:
        return None

    try:
        with open(event_path, encoding="utf-8") as f:
            event_data = json.load(f)
        pr_number = (
            event_data.get("pull_request", {}).get("number")
            or event_data.get("number")
        )
        if pr_number:
            return repo, int(pr_number)
    except Exception:
        pass

    return None
