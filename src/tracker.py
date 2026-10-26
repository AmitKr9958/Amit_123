"""SQLite-backed application tracking and deduplication."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from .config import DATA_DIR, ensure_data_dirs
from .models import ApplicationStatus, ScoredJob

DB_PATH = DATA_DIR / "applied.db"


def _connect() -> sqlite3.Connection:
    ensure_data_dirs()
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    url TEXT NOT NULL,
    score REAL,
    status TEXT NOT NULL,
    reason TEXT,
    applied_at TEXT,
    notes TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applied_at ON applications(applied_at);

CREATE TABLE IF NOT EXISTS run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    jobs_seen INTEGER DEFAULT 0,
    jobs_scored INTEGER DEFAULT 0,
    applied INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    notes TEXT
);
"""


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)


def get_status(job_id: str) -> str | None:
    """Return the stored status for a job, or None if it was never seen."""
    with db() as conn:
        row = conn.execute("SELECT status FROM applications WHERE job_id = ?", (job_id,)).fetchone()
        return row["status"] if row else None


def already_seen(job_id: str) -> bool:
    return get_status(job_id) is not None


def record_scored(scored: ScoredJob, status: ApplicationStatus | None = None) -> None:
    status = status or scored.status
    now = datetime.now().isoformat()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO applications (
                job_id, title, company, url, score, status, reason,
                applied_at, notes, raw_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                score = excluded.score,
                status = excluded.status,
                reason = excluded.reason,
                updated_at = excluded.updated_at,
                raw_json = excluded.raw_json
            """,
            (
                scored.job.job_id,
                scored.job.title,
                scored.job.company,
                scored.job.url,
                scored.score.total,
                status.value,
                "; ".join(scored.score.reasons + scored.score.exclusions) or None,
                None,
                None,
                scored.model_dump_json(),
                now,
                now,
            ),
        )


def mark_applied(job_id: str, reason: str | None = None) -> None:
    now = datetime.now().isoformat()
    with db() as conn:
        conn.execute(
            """
            UPDATE applications
            SET status = ?, applied_at = ?, reason = COALESCE(?, reason), updated_at = ?
            WHERE job_id = ?
            """,
            (ApplicationStatus.APPLIED.value, now, reason, now, job_id),
        )


def mark_status(job_id: str, status: ApplicationStatus, reason: str | None = None) -> None:
    now = datetime.now().isoformat()
    with db() as conn:
        conn.execute(
            """
            UPDATE applications
            SET status = ?, reason = COALESCE(?, reason), updated_at = ?
            WHERE job_id = ?
            """,
            (status.value, reason, now, job_id),
        )


def count_applied_today() -> int:
    today = datetime.now().date().isoformat()
    with db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM applications
            WHERE status = ? AND date(applied_at) = ?
            """,
            (ApplicationStatus.APPLIED.value, today),
        ).fetchone()
        return int(row["c"] if row else 0)


def list_recent(limit: int = 50) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT job_id, title, company, url, score, status, reason, applied_at, updated_at
            FROM applications
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def start_run() -> int:
    now = datetime.now().isoformat()
    with db() as conn:
        cur = conn.execute("INSERT INTO run_log (started_at) VALUES (?)", (now,))
        return int(cur.lastrowid)


def finish_run(
    run_id: int,
    *,
    jobs_seen: int = 0,
    jobs_scored: int = 0,
    applied: int = 0,
    skipped: int = 0,
    failed: int = 0,
    notes: str | None = None,
) -> None:
    now = datetime.now().isoformat()
    with db() as conn:
        conn.execute(
            """
            UPDATE run_log SET
                finished_at = ?, jobs_seen = ?, jobs_scored = ?,
                applied = ?, skipped = ?, failed = ?, notes = ?
            WHERE id = ?
            """,
            (now, jobs_seen, jobs_scored, applied, skipped, failed, notes, run_id),
        )
