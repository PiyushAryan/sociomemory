from __future__ import annotations

import hashlib
import re

_SAFE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


def storage_key(child_id: str) -> str:
    """Return a filename-safe, stable key while preserving existing safe identifiers."""
    if _SAFE_KEY.fullmatch(child_id):
        return child_id
    digest = hashlib.sha256(child_id.encode("utf-8")).hexdigest()
    return f"child-{digest}"
