from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

from sociomemory.time import utc_now


class SQLiteCache:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        provider TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS cache_expires ON cache(expires_at);
    """

    def __init__(self, db_path: str = "~/.sociomemory/cache.db"):
        self._path = Path(db_path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def get(self, key: str) -> Any | None:
        now = utc_now().isoformat()
        row = self._conn.execute(
            "SELECT value FROM cache WHERE key = ? AND expires_at > ?", (key, now)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value: Any, provider: str, ttl_hours: int = 24) -> None:
        now = utc_now()
        expires = (now + timedelta(hours=ttl_hours)).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, provider, created_at, expires_at) VALUES (?,?,?,?,?)",
            (key, json.dumps(value), provider, now.isoformat(), expires),
        )
        self._conn.commit()

    def invalidate(self, key: str) -> None:
        self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        self._conn.commit()

    def purge_expired(self) -> int:
        now = utc_now().isoformat()
        cursor = self._conn.execute("DELETE FROM cache WHERE expires_at <= ?", (now,))
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self._conn.close()
