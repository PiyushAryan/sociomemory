from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DataLevel(str, Enum):
    PUBLIC = "public"
    CONTEXTUAL = "contextual"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"


class NodeType(str, Enum):
    # Entities
    CHILD = "Child"
    PARENT = "Parent"
    FAMILY = "Family"
    # Location hierarchy
    COUNTRY = "Country"
    STATE = "State"
    CITY = "City"
    NEIGHBORHOOD = "Neighborhood"
    PLACE = "Place"
    # Institutional
    SCHOOL = "School"
    EMPLOYER = "Employer"
    THERAPY_CENTER = "TherapyCenter"
    # Context (derived/enriched)
    ECONOMIC = "Economic"
    CULTURAL = "Cultural"
    SAFETY = "Safety"
    TRANSPORT = "Transport"
    REAL_ESTATE = "RealEstate"
    INCOME = "Income"
    # Behavioral / Event
    VISIT = "Visit"
    SENSORY_EVIDENCE = "SensoryEvidence"
    THERAPY_OPPORTUNITY = "TherapyOpportunity"
    # Identity (inferred from behavioral patterns)
    RELIGIOUS = "Religious"
    DIETARY = "Dietary"
    LIFESTYLE = "Lifestyle"
    COMMUNITY = "Community"
    CIVIC = "Civic"
    # Actionable
    IMPLICATION = "Implication"
    TRADEOFF = "Tradeoff"
    # Raw
    SIGNAL = "Signal"


class Node(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    child_id: str
    type: NodeType
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sensitivity: DataLevel = DataLevel.CONTEXTUAL
    document_date: datetime = Field(default_factory=datetime.utcnow)
    event_date: Optional[datetime] = None
    source_chunk: Optional[str] = None  # verbatim conversation snippet
    stale: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_neo4j_props(self) -> dict[str, Any]:
        """Flatten to Neo4j-compatible property dict."""
        props: dict[str, Any] = {
            "id": self.id,
            "child_id": self.child_id,
            "node_type": self.type.value,
            "confidence": self.confidence,
            "sensitivity": self.sensitivity.value,
            "document_date": self.document_date.isoformat(),
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "source_chunk": self.source_chunk,
            "stale": self.stale,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        props.update(self.properties)
        return {k: v for k, v in props.items() if v is not None}

    @classmethod
    def from_neo4j(cls, record: dict, node_type: NodeType, child_id: str) -> "Node":
        """Reconstruct from Neo4j record dict."""
        props = dict(record)
        node_id = props.pop("id", str(uuid.uuid4()))
        props.pop("child_id", None)
        props.pop("node_type", None)
        confidence = float(props.pop("confidence", 1.0))
        sensitivity = DataLevel(props.pop("sensitivity", "contextual"))
        doc_date_str = props.pop("document_date", None)
        document_date = datetime.fromisoformat(doc_date_str) if doc_date_str else datetime.utcnow()
        event_date_str = props.pop("event_date", None)
        event_date = datetime.fromisoformat(event_date_str) if event_date_str else None
        source_chunk = props.pop("source_chunk", None)
        stale = bool(props.pop("stale", False))
        created_str = props.pop("created_at", None)
        updated_str = props.pop("updated_at", None)
        created_at = datetime.fromisoformat(created_str) if created_str else datetime.utcnow()
        updated_at = datetime.fromisoformat(updated_str) if updated_str else datetime.utcnow()
        return cls(
            id=node_id,
            child_id=child_id,
            type=node_type,
            properties=props,
            confidence=confidence,
            sensitivity=sensitivity,
            document_date=document_date,
            event_date=event_date,
            source_chunk=source_chunk,
            stale=stale,
            created_at=created_at,
            updated_at=updated_at,
        )
