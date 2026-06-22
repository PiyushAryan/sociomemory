from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from sociomemory.time import ensure_utc, utc_now


class SignalType(StrEnum):
    LOCATION = "location"
    SCHOOL = "school"
    PARENT_PROFESSION = "profession"
    LANGUAGE = "language"
    HOUSING = "housing"
    TRANSPORT = "transport"
    FAMILY_STRUCTURE = "family"
    VISIT = "visit"
    SENSORY = "sensory"
    RELIGIOUS = "religious"
    DIETARY = "dietary"
    LIFESTYLE = "lifestyle"
    INCOME = "income"
    GENERIC = "generic"


class SignalSource(StrEnum):
    CONVERSATION = "conversation"
    PARENT_FORM = "parent_form"
    PROFILE = "profile"
    INFERRED = "inferred"


class Signal(BaseModel):
    raw_text: str
    signal_type: SignalType
    extracted_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: SignalSource = SignalSource.CONVERSATION
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    place_name: str | None = None
    place_type: str | None = None
    place_subtype: str | None = None
    event_date: datetime | None = None
    mood: str | None = None
    sensory_notes: str | None = None

    _normalize_datetimes = field_validator("timestamp", "event_date")(ensure_utc)
