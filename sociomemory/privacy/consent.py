from __future__ import annotations

import sqlite3
from enum import StrEnum
from pathlib import Path

from sociomemory.time import utc_now


class ConsentScope(StrEnum):
    LOCATION_AREA = "location_area"
    LOCATION_EXACT = "location_exact"
    INCOME_INFERENCE = "income_inference"
    SCHOOL_DATA = "school_data"
    RELIGIOUS_CONTEXT = "religious_context"
    BEHAVIORAL_PROFILING = "behavioral"
    EMPLOYER_DATA = "employer_data"
    EXPORT = "export"


class ConsentManager:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS consent (
        child_id TEXT NOT NULL,
        parent_id TEXT NOT NULL,
        scope TEXT NOT NULL,
        granted INTEGER NOT NULL DEFAULT 0,
        granted_at TEXT NOT NULL,
        PRIMARY KEY (child_id, scope)
    );
    """

    def __init__(self, db_path: str = "~/.sociomemory/consent.db"):
        path = Path(db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(self.SCHEMA)
        self._conn.commit()

    def record_consent(
        self, child_id: str, parent_id: str, scope: ConsentScope, granted: bool = True
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO consent (child_id, parent_id, scope, granted, granted_at) VALUES (?,?,?,?,?)",
            (child_id, parent_id, scope.value, int(granted), utc_now().isoformat()),
        )
        self._conn.commit()

    def check_consent(self, child_id: str, scope: ConsentScope) -> bool:
        row = self._conn.execute(
            "SELECT granted FROM consent WHERE child_id = ? AND scope = ?",
            (child_id, scope.value),
        ).fetchone()
        return bool(row and row[0])

    def get_all_consents(self, child_id: str) -> dict[str, bool]:
        rows = self._conn.execute(
            "SELECT scope, granted FROM consent WHERE child_id = ?", (child_id,)
        ).fetchall()
        return {row[0]: bool(row[1]) for row in rows}

    def revoke_all(self, child_id: str) -> None:
        self._conn.execute("DELETE FROM consent WHERE child_id = ?", (child_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
