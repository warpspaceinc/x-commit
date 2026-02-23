"""SQLite-based analysis cache for x-commit."""

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AnalysisCache:
    """SQLite cache for commit analysis results."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()

        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        logger.info(f"AnalysisCache initialized: {db_path}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_cache (
                        key TEXT PRIMARY KEY,
                        analysis TEXT NOT NULL,
                        model TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _make_key(owner: str, repo: str, sha: str) -> str:
        return f"{owner}/{repo}/{sha}"

    def get(self, owner: str, repo: str, sha: str) -> Optional[str]:
        """Return cached analysis or None on miss."""
        key = self._make_key(owner, repo, sha)
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT analysis FROM analysis_cache WHERE key = ?",
                    (key,),
                ).fetchone()
                if row:
                    logger.info(f"Cache hit: {key}")
                    return row[0]
                logger.info(f"Cache miss: {key}")
                return None
            finally:
                conn.close()

    def put(
        self, owner: str, repo: str, sha: str, analysis: str, model: str
    ) -> None:
        """Store analysis result in cache."""
        key = self._make_key(owner, repo, sha)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis_cache
                        (key, analysis, model, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, analysis, model, now),
                )
                conn.commit()
                logger.info(f"Cache stored: {key}")
            finally:
                conn.close()

    def clear(self) -> int:
        """Delete all cached entries. Returns the number of rows deleted."""
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute("DELETE FROM analysis_cache")
                conn.commit()
                count = cursor.rowcount
                logger.info(f"Cache cleared: {count} entries deleted")
                return count
            finally:
                conn.close()

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            conn = self._connect()
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM analysis_cache"
                ).fetchone()[0]

                oldest = conn.execute(
                    "SELECT MIN(created_at) FROM analysis_cache"
                ).fetchone()[0]

                newest = conn.execute(
                    "SELECT MAX(created_at) FROM analysis_cache"
                ).fetchone()[0]

                db_size = (
                    self._db_path.stat().st_size
                    if self._db_path.exists()
                    else 0
                )

                return {
                    "total_entries": count,
                    "db_path": str(self._db_path),
                    "db_size_bytes": db_size,
                    "oldest_entry": oldest,
                    "newest_entry": newest,
                }
            finally:
                conn.close()
