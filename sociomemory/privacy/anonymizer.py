from __future__ import annotations

import hashlib
import re
from typing import Any


class Anonymizer:
    def __init__(self, salt: str = "sociomemory"):
        self._salt = salt

    def pseudonymize(self, value: str) -> str:
        digest = hashlib.sha256(f"{self._salt}:{value}".encode()).hexdigest()[:8]
        return f"[anon_{digest}]"

    def sanitize_props(
        self, props: dict[str, Any], sensitive_keys: list[str] | None = None
    ) -> dict[str, Any]:
        default_sensitive = {"name", "address", "phone", "email", "id", "aadhaar", "pan"}
        keys_to_redact = set(sensitive_keys or []) | default_sensitive
        return {
            k: self.pseudonymize(v) if k.lower() in keys_to_redact and isinstance(v, str) else v
            for k, v in props.items()
        }

    def anonymize_source_chunk(self, chunk: str) -> str:
        chunk = re.sub(r"\b[6-9]\d{9}\b", "[phone]", chunk)
        chunk = re.sub(r"[\w.+-]+@[\w-]+\.\w+", "[email]", chunk)
        chunk = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[id]", chunk)
        return chunk
