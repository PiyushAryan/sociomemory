from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EdgeType(str, Enum):
    # ----------------------------------------------------------------
    # Relational versioning (supermemory-inspired)
    # ----------------------------------------------------------------
    UPDATES = "UPDATES"       # new fact replaces old; old kept with history
    EXTENDS = "EXTENDS"       # adds detail without contradiction
    DERIVES = "DERIVES"       # second-order inference from combining nodes

    # ----------------------------------------------------------------
    # Structural
    # ----------------------------------------------------------------
    LIVES_IN = "LIVES_IN"
    LOCATED_IN = "LOCATED_IN"
    ATTENDS = "ATTENDS"
    PARENT_OF = "PARENT_OF"
    WORKS_AT = "WORKS_AT"

    # ----------------------------------------------------------------
    # Behavioral (visits, outings, events)
    # ----------------------------------------------------------------
    VISITED = "VISITED"
    AT = "AT"
    FREQUENTS = "FREQUENTS"

    # ----------------------------------------------------------------
    # Proximity (weight = 1/distance_km)
    # ----------------------------------------------------------------
    NEAR_TO = "NEAR_TO"
    ACCESSIBLE_VIA = "ACCESSIBLE_VIA"

    # ----------------------------------------------------------------
    # Contextual
    # ----------------------------------------------------------------
    HAS_CONTEXT = "HAS_CONTEXT"
    INDICATES = "INDICATES"

    # ----------------------------------------------------------------
    # Inference
    # ----------------------------------------------------------------
    IMPLIES = "IMPLIES"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"

    # ----------------------------------------------------------------
    # Provenance
    # ----------------------------------------------------------------
    EXTRACTED_FROM = "EXTRACTED_FROM"

    # ----------------------------------------------------------------
    # Temporal
    # ----------------------------------------------------------------
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl: Optional[datetime] = None  # edge expires (seasonal edges)

    def to_neo4j_props(self) -> dict[str, Any]:
        props: dict[str, Any] = {
            "id": self.id,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl.isoformat() if self.ttl else None,
        }
        props.update(self.properties)
        return {k: v for k, v in props.items() if v is not None}
