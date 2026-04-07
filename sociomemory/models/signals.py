from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
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


class SignalSource(str, Enum):
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # For visit signals
    place_name: Optional[str] = None
    place_type: Optional[str] = None
    place_subtype: Optional[str] = None
    event_date: Optional[datetime] = None
    mood: Optional[str] = None
    sensory_notes: Optional[str] = None
