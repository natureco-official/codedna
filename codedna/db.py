"""SQLite database CRUD operations."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

# Default database path
DB_PATH = Path.home() / ".codedna" / "codedna.db"


def get_db_path(repo_path: Optional[Path] = None) -> Path:
    """Return the repo-specific database path."""
    if repo_path:
        return repo_path / ".codedna.db"
    return DB_PATH


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Manage a SQLite connection with a context manager."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Create the database schema if it does not exist."""
    with get_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS commits (
                id INTEGER PRIMARY KEY,
                commit_hash TEXT UNIQUE,
                author TEXT,
                timestamp INTEGER,
                files_changed INTEGER,
                understanding_score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS file_scores (
                id INTEGER PRIMARY KEY,
                commit_hash TEXT,
                file_path TEXT,
                ai_probability REAL,
                complexity_score REAL,
                comment_ratio REAL,
                understanding_score REAL,
                ai_tool_guess TEXT,
                FOREIGN KEY (commit_hash) REFERENCES commits(commit_hash)
            );

            CREATE TABLE IF NOT EXISTS file_ownership (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                author TEXT,
                lines_owned INTEGER,
                last_touched INTEGER,
                avg_understanding REAL,
                UNIQUE(file_path, author)
            );

            CREATE TABLE IF NOT EXISTS sprints (
                id INTEGER PRIMARY KEY,
                sprint_name TEXT,
                start_date INTEGER,
                end_date INTEGER,
                total_lines_ai INTEGER,
                total_lines_human INTEGER,
                avg_understanding REAL,
                debt_delta_hours REAL,
                health_score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS protected_modules (
                id INTEGER PRIMARY KEY,
                file_path TEXT UNIQUE,
                min_understanding_threshold REAL DEFAULT 3.5,
                label TEXT,
                added_by TEXT,
                added_at INTEGER,
                last_alert_at INTEGER,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS interview_sessions (
                id INTEGER PRIMARY KEY,
                candidate_name TEXT,
                file_path TEXT,
                started_at INTEGER,
                completed_at INTEGER,
                questions_json TEXT,
                comprehension_score REAL,
                time_taken_seconds INTEGER,
                evaluator_notes TEXT,
                created_by TEXT
            );
        """)


def save_commit(
    commit_hash: str,
    author: str,
    timestamp: int,
    files_changed: int,
    understanding_score: Optional[float],
    db_path: Optional[Path] = None,
) -> None:
    """Save or update a commit record."""
    with get_connection(db_path) as conn:
        if understanding_score is not None:
            conn.execute(
                """
                INSERT INTO commits (commit_hash, author, timestamp, files_changed, understanding_score)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(commit_hash) DO UPDATE SET
                    understanding_score = excluded.understanding_score
                """,
                (commit_hash, author, timestamp, files_changed, understanding_score),
            )
        else:
            conn.execute(
                """
                INSERT INTO commits (commit_hash, author, timestamp, files_changed, understanding_score)
                VALUES (?, ?, ?, ?, NULL)
                ON CONFLICT(commit_hash) DO NOTHING
                """,
                (commit_hash, author, timestamp, files_changed),
            )


def save_file_score(
    commit_hash: str,
    file_path: str,
    ai_probability: float,
    complexity_score: float,
    comment_ratio: float,
    understanding_score: Optional[float] = None,
    ai_tool_guess: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Save a file analysis score."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO file_scores
                (commit_hash, file_path, ai_probability, complexity_score, comment_ratio, understanding_score, ai_tool_guess)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (commit_hash, file_path, ai_probability, complexity_score, comment_ratio, understanding_score, ai_tool_guess),
        )


def get_commit_history(limit: int = 20, db_path: Optional[Path] = None) -> list[sqlite3.Row]:
    """Return the last N commits sorted by date."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM commits
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def get_file_scores_for_commit(commit_hash: str, db_path: Optional[Path] = None) -> list[sqlite3.Row]:
    """Return file scores for a specific commit."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM file_scores WHERE commit_hash = ?",
            (commit_hash,),
        ).fetchall()
    return rows


def get_latest_commit(db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Return the most recently saved commit."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM commits ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    return row


def get_latest_understanding_for_file(
    file_path: str, db_path: Optional[Path] = None
) -> Optional[float]:
    """Return the most recent understanding score for a specific file."""
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


def get_all_file_understanding_scores(
    db_path: Optional[Path] = None,
) -> dict[str, float]:
    """
    Return the most recent understanding score for all files as a dict.
    Format: {file_path: understanding_score}.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT fs.file_path, fs.understanding_score
            FROM file_scores fs
            JOIN commits c ON fs.commit_hash = c.commit_hash
            WHERE fs.understanding_score IS NOT NULL
              AND c.timestamp = (
                  SELECT MAX(c2.timestamp)
                  FROM file_scores fs2
                  JOIN commits c2 ON fs2.commit_hash = c2.commit_hash
                  WHERE fs2.file_path = fs.file_path
                    AND fs2.understanding_score IS NOT NULL
              )
            """,
        ).fetchall()
    return {r["file_path"]: float(r["understanding_score"]) for r in rows}


def update_understanding_score(
    commit_hash: str,
    understanding_score: float,
    db_path: Optional[Path] = None,
) -> None:
    """Update the understanding score for a commit and its associated files."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE commits SET understanding_score = ? WHERE commit_hash = ?",
            (understanding_score, commit_hash),
        )
        # Also update all file scores belonging to this commit
        conn.execute(
            "UPDATE file_scores SET understanding_score = ? WHERE commit_hash = ?",
            (understanding_score, commit_hash),
        )


def upsert_file_ownership(
    file_path: str,
    author: str,
    lines_owned: int,
    last_touched: int,
    avg_understanding: Optional[float] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Insert or update a file ownership record."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO file_ownership
                (file_path, author, lines_owned, last_touched, avg_understanding)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path, author) DO UPDATE SET
                lines_owned      = excluded.lines_owned,
                last_touched     = excluded.last_touched,
                avg_understanding = COALESCE(excluded.avg_understanding, avg_understanding)
            """,
            (file_path, author, lines_owned, last_touched, avg_understanding),
        )


def get_file_ownership(
    file_path: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[sqlite3.Row]:
    """
    Return file ownership records.

    Args:
        file_path: Filter by a specific file (all files if None)
    """
    with get_connection(db_path) as conn:
        if file_path:
            rows = conn.execute(
                "SELECT * FROM file_ownership WHERE file_path = ? ORDER BY lines_owned DESC",
                (file_path,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM file_ownership ORDER BY file_path, lines_owned DESC"
            ).fetchall()
    return rows


def save_sprint(
    sprint_name: str,
    start_date: int,
    end_date: int,
    total_lines_ai: int,
    total_lines_human: int,
    avg_understanding: Optional[float],
    debt_delta_hours: Optional[float],
    health_score: Optional[float],
    db_path: Optional[Path] = None,
) -> int:
    """Create a sprint record and return the new record's id."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO sprints
                (sprint_name, start_date, end_date, total_lines_ai, total_lines_human,
                 avg_understanding, debt_delta_hours, health_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sprint_name, start_date, end_date, total_lines_ai, total_lines_human,
             avg_understanding, debt_delta_hours, health_score),
        )
        return cur.lastrowid or 0


def get_sprint_history(
    limit: int = 10,
    db_path: Optional[Path] = None,
) -> list[sqlite3.Row]:
    """Return past sprints sorted by date."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM sprints ORDER BY start_date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows


def get_latest_sprint(db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Return the most recent sprint record."""
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM sprints ORDER BY start_date DESC LIMIT 1"
        ).fetchone()


def export_all_data(db_path: Optional[Path] = None) -> dict:
    """Export all database data as a serializable dict."""
    with get_connection(db_path) as conn:
        commits = [
            dict(r) for r in conn.execute(
                "SELECT * FROM commits ORDER BY timestamp DESC"
            ).fetchall()
        ]
        file_scores = [
            dict(r) for r in conn.execute(
                "SELECT * FROM file_scores ORDER BY commit_hash DESC"
            ).fetchall()
        ]
        sprints = [
            dict(r) for r in conn.execute(
                "SELECT * FROM sprints ORDER BY start_date DESC"
            ).fetchall()
        ]
        protected = [
            dict(r) for r in conn.execute(
                "SELECT * FROM protected_modules ORDER BY added_at DESC"
            ).fetchall()
        ]
        ownership = [
            dict(r) for r in conn.execute(
                "SELECT * FROM file_ownership ORDER BY file_path"
            ).fetchall()
        ]
        interviews = [
            dict(r) for r in conn.execute(
                "SELECT * FROM interview_sessions ORDER BY started_at DESC"
            ).fetchall()
        ]

    # Convert datetime objects to strings
    for table in [commits, file_scores, sprints, protected, ownership, interviews]:
        for row in table:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()

    return {
        "commits": commits,
        "file_scores": file_scores,
        "sprints": sprints,
        "protected_modules": protected,
        "file_ownership": ownership,
        "interview_sessions": interviews,
        "exported_at": datetime.now().isoformat(),
    }


def get_commit_count(db_path: Optional[Path] = None) -> int:
    """Return total number of commits recorded."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM commits").fetchone()
        return row["cnt"] if row else 0


def get_file_score_count(db_path: Optional[Path] = None) -> int:
    """Return total number of file scores recorded."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM file_scores").fetchone()
        return row["cnt"] if row else 0


def import_data(data: dict, db_path: Optional[Path] = None) -> dict:
    """Import data from an export dict. Returns counts of imported records."""
    counts = {"commits": 0, "file_scores": 0, "sprints": 0}
    with get_connection(db_path) as conn:
        for commit in data.get("commits", []):
            conn.execute(
                """INSERT OR IGNORE INTO commits (commit_hash, author, timestamp, files_changed, understanding_score)
                   VALUES (?, ?, ?, ?, ?)""",
                (commit.get("commit_hash"), commit.get("author"),
                 commit.get("timestamp"), commit.get("files_changed"),
                 commit.get("understanding_score")),
            )
            counts["commits"] += 1

        for fs in data.get("file_scores", []):
            conn.execute(
                """INSERT OR IGNORE INTO file_scores (commit_hash, file_path, ai_probability, complexity_score, comment_ratio, understanding_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (fs.get("commit_hash"), fs.get("file_path"),
                 fs.get("ai_probability"), fs.get("complexity_score"),
                 fs.get("comment_ratio"), fs.get("understanding_score")),
            )
            counts["file_scores"] += 1

        for sprint in data.get("sprints", []):
            conn.execute(
                """INSERT OR IGNORE INTO sprints (sprint_name, start_date, end_date, total_lines_ai, total_lines_human, avg_understanding, debt_delta_hours, health_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (sprint.get("sprint_name"), sprint.get("start_date"),
                 sprint.get("end_date"), sprint.get("total_lines_ai"),
                 sprint.get("total_lines_human"), sprint.get("avg_understanding"),
                 sprint.get("debt_delta_hours"), sprint.get("health_score")),
            )
            counts["sprints"] += 1

    return counts


def get_trend_data(db_path: Optional[Path] = None, limit: int = 30) -> list[dict]:
    """Return time-series data for trend charts: day-by-day avg AI and understanding."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                date(c.timestamp, 'unixepoch') as day,
                AVG(c.understanding_score) as avg_understanding,
                AVG(fs.ai_probability) as avg_ai_probability,
                COUNT(DISTINCT c.commit_hash) as commit_count,
                COUNT(fs.id) as file_count
            FROM commits c
            LEFT JOIN file_scores fs ON c.commit_hash = fs.commit_hash
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
