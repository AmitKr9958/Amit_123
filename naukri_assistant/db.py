"""SQLite persistence, URL de-duplication, and application status tracking."""
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


class JobStore:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL,
                company TEXT NOT NULL, location TEXT NOT NULL, experience TEXT NOT NULL,
                posted_text TEXT NOT NULL, summary TEXT NOT NULL, search_query TEXT NOT NULL,
                match_score INTEGER NOT NULL, matched_skills TEXT NOT NULL,
                excluded_reasons TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'saved',
                first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, raw_json TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def upsert_job(self, job: dict) -> str:
        url = canonical_url(job.get("url", ""))
        if not url:
            return "invalid"
        job["url"] = url
        job_id = str(job.get("job_id") or url)
        now = job.get("matched_at", "")
        old = self.conn.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone()
        values = (
            url, job.get("title", "Unknown"), job.get("company", "Unknown"),
            job.get("location", "Unknown"), job.get("experience", ""), job.get("posted_text", ""),
            job.get("description", ""), job.get("search_query", ""), int(job.get("match_score", 0)),
            job.get("matched_skills", ""), job.get("excluded_reasons", ""), now,
            json.dumps(job, ensure_ascii=False), job_id
        )
        if old:
            self.conn.execute("""UPDATE jobs SET url=?,title=?,company=?,location=?,experience=?,posted_text=?,
                summary=?,search_query=?,match_score=?,matched_skills=?,excluded_reasons=?,last_seen=?,raw_json=?
                WHERE id=?""", values)
            self.conn.commit()
            return "seen"
        self.conn.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            job_id, url, job.get("title", "Unknown"), job.get("company", "Unknown"),
            job.get("location", "Unknown"), job.get("experience", ""), job.get("posted_text", ""),
            job.get("description", ""), job.get("search_query", ""), int(job.get("match_score", 0)),
            job.get("matched_skills", ""), job.get("excluded_reasons", ""), "saved", now, now,
            json.dumps(job, ensure_ascii=False)
        ))
        self.conn.commit()
        return "new"

    def list_jobs(self, limit=50, status=None):
        sql, params = "SELECT * FROM jobs", []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY match_score DESC, last_seen DESC LIMIT ?"
        params.append(max(1, min(int(limit), 10000)))
        rows = self.conn.execute(sql, params).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item.pop("raw_json", None)
        return items

    def get_job(self, job_id):
        row = self.conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def update_status(self, job_id, status):
        cur = self.conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        self.conn.commit()
        return cur.rowcount > 0
