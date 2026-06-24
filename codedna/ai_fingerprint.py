"""
Distinguishes patterns left by different AI code assistants.

IMPORTANT WARNING:
  This is NOT a definitive detection — it is a pattern-based heuristic ESTIMATION model.
  Results may contain false positives/negatives. No certainty is claimed.
  Must be presented to users with this context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection


# ---------------------------------------------------------------------------
# Tool pattern definitions — heuristic, defensible but not definitive
# ---------------------------------------------------------------------------

# Weighted pattern list per tool: (regex_pattern, weight)
_TOOL_PATTERNS: dict[str, list[tuple[str, float]]] = {
    "copilot": [
        # GitHub Copilot: short inline comments, no type declarations
        (r"#\s+[A-Z][a-z].{5,40}$", 0.15),           # single-line title comment
        (r"def \w+\([^)]{0,30}\):\s*$", 0.10),        # no-param / minimal function
        (r"#\s+TODO:", 0.10),                          # TODO comments
        (r"^\s{4}pass\s*$", 0.08),                     # functions ending with pass
        (r"return \w+\.get\(", 0.07),                  # .get() pattern
    ],
    "cursor": [
        # Cursor: detailed docstrings, rich type hints
        (r'"""[\s\S]{20,200}"""', 0.20),               # long docstring
        (r":\s*(str|int|float|bool|list|dict|Optional)", 0.15),  # type hints
        (r"->.*:\s*$", 0.12),                          # return type declaration
        (r"from typing import", 0.10),                 # typing module
        (r"@dataclass", 0.10),                         # dataclass usage
    ],
    "claude": [
        # Claude: structured multi-line comments, Args/Returns docstrings
        (r"#\s+\d+\.\s+\w", 0.18),                    # numbered step comments
        (r"\"\"\"[\s\S]*Args:[\s\S]*Returns:", 0.20),  # Args/Returns docstring
        (r"#\s+─{3,}", 0.15),                          # separator line comments
        (r"raise \w+Error\(f[\"']", 0.10),             # f-string error messages
        (r"from __future__ import annotations", 0.12), # modern annotation
    ],
}

# Minimum confidence threshold — returns "unknown" if below this
_MIN_CONFIDENCE = 0.15


@dataclass
class AIToolGuess:
    """AI tool guess for a single file."""

    tool: str              # "copilot" | "cursor" | "claude" | "unknown"
    confidence: float      # 0.0–1.0
    score_detail: dict[str, float]  # tool → raw score
    warning: str = (
        "This detection is pattern-based estimation — not definitive."
    )


def guess_ai_tool(file_path: str, code: str) -> AIToolGuess:
    """
    Return a probable AI tool guess and confidence score for a file.

    Strategy:
      Defined regex patterns for each tool are applied to the code.
      A total score is computed based on weighted match counts.
      The highest-scoring tool is selected if it exceeds the minimum confidence threshold.

    Args:
        file_path: File path (used for extension filtering)
        code: Source code of the file

    Returns:
        AIToolGuess object
    """
    lines = code.splitlines()
    scores: dict[str, float] = {tool: 0.0 for tool in _TOOL_PATTERNS}

    for tool, patterns in _TOOL_PATTERNS.items():
        for pattern, weight in patterns:
            match_count = sum(1 for line in lines if re.search(pattern, line))
            # Normalize by line count (prevents unfair advantage in large files)
            norm = match_count / max(len(lines), 1)
            scores[tool] += norm * weight * 10  # scale to 0–10

    # Normalize — calculate confidence relative to total score
    total = sum(scores.values())
    if total < 0.01:
        return AIToolGuess(
            tool="unknown",
            confidence=0.0,
            score_detail={k: round(v, 3) for k, v in scores.items()},
        )

    best_tool = max(scores, key=lambda k: scores[k])
    confidence = scores[best_tool] / total

    # Below minimum threshold → unknown
    if confidence < _MIN_CONFIDENCE:
        best_tool = "unknown"

    return AIToolGuess(
        tool=best_tool,
        confidence=round(confidence, 3),
        score_detail={k: round(v, 3) for k, v in scores.items()},
    )


def analyze_repo_tools(
    repo_path: Path,
    db_path: Path,
) -> dict[str, dict[str, float]]:
    """
    Run a tool-based file analysis across the repo and save results to DB.

    Returns:
        {tool: {"file_count": N, "avg_ai_probability": X}} dict
    """
    from codedna.scorer import scan_repository

    supported = {".py", ".js", ".jsx", ".ts", ".tsx"}
    results = scan_repository(repo_path, max_files=200)

    # Tool counters
    tool_stats: dict[str, dict[str, list]] = {
        "copilot": {"ai_prob": [], "understanding": []},
        "cursor":  {"ai_prob": [], "understanding": []},
        "claude":  {"ai_prob": [], "understanding": []},
        "unknown": {"ai_prob": [], "understanding": []},
    }

    for result in results:
        if Path(result.file_path).suffix.lower() not in supported:
            continue
        try:
            code = Path(result.file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        guess = guess_ai_tool(result.file_path, code)

        # Save to DB — update the most recent file_score record
        try:
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    UPDATE file_scores
                    SET ai_tool_guess = ?
                    WHERE file_path = ?
                      AND id = (
                          SELECT id FROM file_scores
                          WHERE file_path = ?
                          ORDER BY id DESC LIMIT 1
                      )
                    """,
                    (guess.tool, result.file_path, result.file_path),
                )
        except Exception:
            pass

        if guess.tool in tool_stats:
            tool_stats[guess.tool]["ai_prob"].append(result.ai_probability)
        else:
            tool_stats["unknown"]["ai_prob"].append(result.ai_probability)

    # Collect understanding scores per tool from DB
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT fs.ai_tool_guess, fs.understanding_score
                FROM file_scores fs
                WHERE fs.ai_tool_guess IS NOT NULL
                  AND fs.understanding_score IS NOT NULL
                """
            ).fetchall()
            for r in rows:
                tool = r["ai_tool_guess"] or "unknown"
                if tool in tool_stats:
                    tool_stats[tool]["understanding"].append(
                        float(r["understanding_score"])
                    )
    except Exception:
        pass

    # Compute output
    output: dict[str, dict[str, float]] = {}
    for tool, data in tool_stats.items():
        if not data["ai_prob"]:
            continue
        avg_ai = sum(data["ai_prob"]) / len(data["ai_prob"])
        avg_und = (
            sum(data["understanding"]) / len(data["understanding"])
            if data["understanding"] else None
        )
        output[tool] = {
            "file_count": len(data["ai_prob"]),  # kept for API compat
            "avg_ai_probability": round(avg_ai, 3),
            "avg_understanding": round(avg_und, 2) if avg_und is not None else None,
        }

    return output


def compare_tools_in_repo(repo_path: Path, db_path: Path) -> dict:
    """
    Compare average understanding scores and AI probabilities per tool across the repo.

    Returns:
        {"copilot": {...}, "cursor": {...}, ...} dict
    """
    return analyze_repo_tools(repo_path, db_path)
