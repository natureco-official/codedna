"""SQLite veritabanı CRUD işlemleri."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

# Varsayılan veritabanı yolu
DB_PATH = Path.home() / ".codedna" / "codedna.db"


def get_db_path(repo_path: Optional[Path] = None) -> Path:
    """Repo'ya özgü veritabanı yolunu döndür."""
    if repo_path:
        return repo_path / ".codedna.db"
    return DB_PATH


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """SQLite bağlantısını context manager ile yönet."""
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
    """Veritabanı şemasını oluştur (yoksa)."""
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
    """Commit bilgisini kaydet veya güncelle."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO commits (commit_hash, author, timestamp, files_changed, understanding_score)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(commit_hash) DO UPDATE SET
                understanding_score = excluded.understanding_score
            """,
            (commit_hash, author, timestamp, files_changed, understanding_score),
        )


def save_file_score(
    commit_hash: str,
    file_path: str,
    ai_probability: float,
    complexity_score: float,
    comment_ratio: float,
    understanding_score: Optional[float] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Dosya analiz skorunu kaydet."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO file_scores
                (commit_hash, file_path, ai_probability, complexity_score, comment_ratio, understanding_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_hash, file_path, ai_probability, complexity_score, comment_ratio, understanding_score),
        )


def get_commit_history(limit: int = 20, db_path: Optional[Path] = None) -> list[sqlite3.Row]:
    """Son N commit'i tarihe göre sıralı getir."""
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
    """Belirli bir commit'e ait dosya skorlarını getir."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM file_scores WHERE commit_hash = ?",
            (commit_hash,),
        ).fetchall()
    return rows


def get_latest_commit(db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """En son kaydedilen commit'i getir."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM commits ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    return row


def get_latest_understanding_for_file(
    file_path: str, db_path: Optional[Path] = None
) -> Optional[float]:
    """Belirli bir dosyanın en son anlama skorunu getir."""
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
    Tüm dosyaların en son anlama skorlarını dict olarak getir.
    {file_path: understanding_score} formatında döner.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT fs.file_path, fs.understanding_score
            FROM file_scores fs
            JOIN commits c ON fs.commit_hash = c.commit_hash
            WHERE fs.understanding_score IS NOT NULL
            GROUP BY fs.file_path
            HAVING c.timestamp = MAX(c.timestamp)
            """,
        ).fetchall()
    return {r["file_path"]: float(r["understanding_score"]) for r in rows}


def update_understanding_score(
    commit_hash: str,
    understanding_score: float,
    db_path: Optional[Path] = None,
) -> None:
    """Commit'in ve ilgili dosyaların anlama skorunu güncelle."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE commits SET understanding_score = ? WHERE commit_hash = ?",
            (understanding_score, commit_hash),
        )
        # Aynı commit'e ait tüm dosya skorlarını da güncelle
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
    """Dosya sahiplik kaydını ekle veya güncelle."""
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
    Dosya sahiplik kayıtlarını getir.

    Args:
        file_path: Belirli bir dosya filtrele (None ise tüm dosyalar)
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
    """Sprint kaydı oluştur, yeni kaydın id'sini döndür."""
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
    """Geçmiş sprint'leri tarihe göre sıralı getir."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM sprints ORDER BY start_date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows


def get_latest_sprint(db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """En son sprint kaydını getir."""
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM sprints ORDER BY start_date DESC LIMIT 1"
        ).fetchone()
