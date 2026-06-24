"""
Candidate evaluation — codebase comprehension test.

IMPORTANT WARNING:
  This tool does NOT replace human evaluation. It is a supplementary signal.
  It must not be used as the sole basis for hiring decisions.
  Automatic scoring is intentionally excluded — the human evaluator enters scores manually.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from codedna.db import get_connection

# Difficulty → complexity score thresholds
_DIFFICULTY_THRESHOLDS = {
    "easy":   (0.0, 5.0),    # low complexity
    "medium": (5.0, 15.0),   # medium complexity
    "hard":   (15.0, 999.),  # high complexity
}

# Anonymization: replace common identifiers with generic names
_ANONYMIZATION_PATTERNS: list[tuple[str, str]] = [
    (r'\b(payment|charge|invoice|billing)\b', 'transaction'),
    (r'\b(user|account|customer|member)\b', 'entity'),
    (r'\b(password|secret|token|key|credential)\b', 'credential'),
    (r'\b(database|db|repository|repo|store)\b', 'storage'),
    (r'\b(email|phone|address|contact)\b', 'contact_info'),
]


@dataclass
class CandidateFile:
    """File information selected for an interview."""

    file_path: str           # kept for API compatibility (was: dosya_yolu)
    anonymized_code: str  # kept for API compatibility (was: anonimlestirilmis_kod)
    complexity_score: float    # kept for API compatibility (was: karmasiklik_skoru)
    difficulty: str
    line_count: int           # kept for API compatibility (was: satir_sayisi)


def _anonymize_code(code: str) -> str:
    """
    Anonymize source code — replace identifiers that reveal business logic
    with generic names. Preserves code structure and logic.

    Args:
        code: Raw source code

    Returns:
        Anonymized code
    """
    result = code
    for pattern, replacement in _ANONYMIZATION_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def select_candidate_file(
    repo_path: Path,
    db_path: Path,
    difficulty: str = "medium",
) -> Optional[CandidateFile]:
    """
    Select a suitable file from the repo for an interview.

    Selection criteria:
      - Complexity score within the requested difficulty range
      - Protected modules are NEVER selected
      - At least 20, at most 200 lines
      - Supported extension (.py, .js, .ts)

    Args:
        repo_path: Git repo root directory
        db_path: SQLite database path
        difficulty: "easy" | "medium" | "hard"

    Returns:
        CandidateFile object, or None if no suitable file found
    """
    from codedna.scorer import scan_repository
    from codedna.protection import check_protected_modules

    low, high = _DIFFICULTY_THRESHOLDS.get(difficulty, _DIFFICULTY_THRESHOLDS["medium"])

    # Get protected modules — never select these
    protected = {m.file_path for m in check_protected_modules(db_path)}

    scanned = scan_repository(repo_path, max_files=200)

    eligible = [
        s for s in scanned
        if low <= s.complexity_score < high
        and s.file_path not in protected
        and 20 <= s.total_lines <= 200
    ]

    if not eligible:
        return None

    # Select the file closest to the midpoint complexity (not too easy/hard)
    eligible.sort(key=lambda s: abs(s.complexity_score - (low + high) / 2))
    selected = eligible[0]

    try:
        code = Path(selected.file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    anonymized = _anonymize_code(code)

    return CandidateFile(
        file_path=selected.file_path,
        anonymized_code=anonymized,
        complexity_score=round(selected.complexity_score, 1),
        difficulty=difficulty,
        line_count=selected.total_lines,
    )


def generate_questions(code: str) -> list[str]:
    """
    Automatically generate 3 comprehension questions from code.

    Template-based generation — no AI call required, inferred from code structure.
    Generated questions are always generic, not tied to specific business logic.

    Args:
        code: Source code (may be anonymized)

    Returns:
        List of 3 questions
    """
    lines = code.splitlines()
    function_count = sum(
        1 for line in lines
        if re.match(r'\s*(def |function |async function )', line)
    )
    branch_count = sum(
        1 for line in lines
        if re.search(r'\b(if|else|elif|for|while|try|except|catch)\b', line)
    )
    has_return = any("return " in line for line in lines)

    questions = [
        "After reading this code, what is the primary purpose of the main function/method?",
        f"This code contains {function_count} function(s)/method(s). "
        f"Which one carries the most critical business logic, and why?",
    ]

    if branch_count > 3:
        questions.append(
            f"There are {branch_count} branches/conditions in the code. "
            f"Which condition handles the most important error scenario?"
        )
    elif has_return:
        questions.append(
            "Under what condition could this function return an unexpected value? "
            "How would you debug that scenario?"
        )
    else:
        questions.append(
            "If you had to write a test for this code, which behavior would you test first?"
        )

    return questions[:3]


def start_session(
    candidate_name: str,
    file_path: str,
    questions: list[str],
    db_path: Path,
    created_by: str = "system",
) -> int:
    """
    Start a new interview session.

    Args:
        candidate_name: Candidate name
        file_path: Path of the file being tested
        questions: List of questions asked
        db_path: SQLite database path
        created_by: Who started the session

    Returns:
        New session id
    """
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO interview_sessions
                (candidate_name, file_path, started_at, questions_json, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                candidate_name,
                file_path,
                int(time.time()),
                json.dumps(questions, ensure_ascii=False),
                created_by,
            ),
        )
        return cur.lastrowid or 0


def submit_score(
    session_id: int,
    score: float,
    evaluator_notes: str,
    db_path: Path,
) -> dict:
    """
    Save the score given by the human evaluator.

    Automatic scoring is intentionally absent — it can be misleading,
    so human evaluation is required in this phase.

    Args:
        session_id: Session id
        score: Score between 0.0 and 5.0
        evaluator_notes: Evaluator notes
        db_path: SQLite database path

    Returns:
        Updated session summary
    """
    if not (0.0 <= score <= 5.0):
        raise ValueError(f"Score must be between 0.0 and 5.0, got: {score}")

    now = int(time.time())
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE interview_sessions
            SET comprehension_score = ?,
                evaluator_notes     = ?,
                completed_at        = ?
            WHERE id = ?
            """,
            (score, evaluator_notes, now, session_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Session #{session_id} not found.")

    return {
        "session_id": session_id,
        "comprehension_score": score,
        "evaluator_notes": evaluator_notes,
        "message": "Evaluation saved.",
    }


def get_sessions(db_path: Path, limit: int = 20) -> list[dict]:
    """Return past interview sessions."""
    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, candidate_name, file_path, started_at, completed_at,
                       comprehension_score, evaluator_notes, created_by
                FROM interview_sessions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except Exception:
        return []

    def _ts(ts: Optional[int]) -> Optional[str]:
        if not ts:
            return None
        from datetime import datetime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    return [
        {
            "id": r["id"],
            "candidate": r["candidate_name"],
            "file_path": r["file_path"],
            "start_time": _ts(r["started_at"]),
            "end_time": _ts(r["completed_at"]),
            "score": r["comprehension_score"],
            "notes": r["evaluator_notes"],
            "created_by": r["created_by"],
        }
        for r in rows
    ]
