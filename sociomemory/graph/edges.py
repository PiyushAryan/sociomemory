from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from sociomemory.time import ensure_utc, utc_now


class EdgeType(StrEnum):
    UPDATES = "UPDATES"
    EXTENDS = "EXTENDS"
    DERIVES = "DERIVES"

    LIVES_IN = "LIVES_IN"
    LOCATED_IN = "LOCATED_IN"
    ATTENDS = "ATTENDS"
    PARENT_OF = "PARENT_OF"
    WORKS_AT = "WORKS_AT"

    VISITED = "VISITED"
    AT = "AT"
    FREQUENTS = "FREQUENTS"

    NEAR_TO = "NEAR_TO"
    ACCESSIBLE_VIA = "ACCESSIBLE_VIA"

    HAS_CONTEXT = "HAS_CONTEXT"
    INDICATES = "INDICATES"

    IMPLIES = "IMPLIES"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"

    EXTRACTED_FROM = "EXTRACTED_FROM"

    SEASONAL = "SEASONAL"
    PART_OF = "PART_OF"
    FOLLOWS = "FOLLOWS"


class Edge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    type: EdgeType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    ttl: datetime | None = None

    _normalize_datetimes = field_validator("created_at", "ttl")(ensure_utc)

    def to_storage_props(self) -> dict[str, Any]:
        props: dict[str, Any] = {
            "id": self.id,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl.isoformat() if self.ttl else None,
        }
        props.update(self.properties)
        return {k: v for k, v in props.items() if v is not None}

    def to_neo4j_props(self) -> dict[str, Any]:
        """Backward-compatible alias for older integrations."""
        return self.to_storage_props()
