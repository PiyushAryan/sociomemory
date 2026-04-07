from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from sociomemory.models.signals import Signal, SignalSource, SignalType

if TYPE_CHECKING:
    from sociomemory.llm.base import BaseLLM

logger = logging.getLogger(__name__)

LOCATION_PATTERNS = [
    r"(?:i live|we live|staying|stay|residing|house|home|flat|apartment)\s+(?:in|at|near)\s+([A-Z][a-zA-Z\s,]+)",
    r"(?:my|our)\s+(?:area|locality|neighborhood|neighbourhood|colony)\s+(?:is|in)\s+([A-Z][a-zA-Z\s,]+)",
]

SCHOOL_PATTERNS = [
    r"(?:goes?|going|study|studies|attending)\s+(?:to\s+)?([A-Z][a-zA-Z\s]+(?:School|Academy|Institute|Vidyalaya|Convent|Public|International))",
    r"(?:school|college)\s+(?:is|name is|called)\s+([A-Z][a-zA-Z\s]+)",
]

PROFESSION_PATTERNS = [
    r"(?:papa|dad|father|mummy|mom|mother|parent)\s+(?:works?|working|job|employed)\s+(?:at|in|for)\s+([A-Z][a-zA-Z\s]+)",
    r"(?:papa|dad|father|mummy|mom|mother)\s+(?:is\s+(?:a|an)\s+)?([a-zA-Z\s]+(?:engineer|doctor|teacher|manager|developer|analyst|officer|director|consultant|accountant))",
]

PLACE_TYPES = {
    "iskcon": ("religious", "iskcon"),
    "temple": ("religious", "temple"),
    "mosque": ("religious", "mosque"),
    "church": ("religious", "church"),
    "gurudwara": ("religious", "gurudwara"),
    "park": ("outdoor", "park"),
    "playground": ("outdoor", "playground"),
    "mall": ("urban", "mall"),
    "museum": ("cultural", "museum"),
    "zoo": ("outdoor", "zoo"),
    "beach": ("outdoor", "beach"),
    "mountain": ("outdoor", "mountain"),
    "hill station": ("outdoor", "hill_station"),
    "water park": ("outdoor", "water_park"),
    "snow park": ("outdoor", "snow_park"),
    "library": ("cultural", "library"),
}


class SignalExtractor:
    """Extract structured signals from raw conversation text."""

    def __init__(self, llm: "BaseLLM | None" = None):
        self._llm = llm

    async def extract(self, text: str, source: SignalSource = SignalSource.CONVERSATION) -> list[Signal]:
        signals: list[Signal] = []
        now = datetime.utcnow()
        signals.extend(self._extract_location(text, source, now))
        signals.extend(self._extract_school(text, source, now))
        signals.extend(self._extract_profession(text, source, now))
        signals.extend(self._extract_visit(text, source, now))
        if self._llm and not signals:
            signals.extend(await self._llm_extract(text, source, now))
        return signals

    def _extract_location(self, text: str, source: SignalSource, now: datetime) -> list[Signal]:
        results = []
        for pattern in LOCATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(1).strip().rstrip(",. ")
                if len(val) >= 3:
                    results.append(Signal(
                        raw_text=text, signal_type=SignalType.LOCATION,
                        extracted_value=val, confidence=0.85, source=source, timestamp=now,
                    ))
        return results

    def _extract_school(self, text: str, source: SignalSource, now: datetime) -> list[Signal]:
        results = []
        for pattern in SCHOOL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(1).strip()
                if len(val) >= 3:
                    results.append(Signal(
                        raw_text=text, signal_type=SignalType.SCHOOL,
                        extracted_value=val, confidence=0.9, source=source, timestamp=now,
                    ))
        return results

    def _extract_profession(self, text: str, source: SignalSource, now: datetime) -> list[Signal]:
        results = []
        for pattern in PROFESSION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(1).strip()
                if len(val) >= 3:
                    results.append(Signal(
                        raw_text=text, signal_type=SignalType.PARENT_PROFESSION,
                        extracted_value=val, confidence=0.8, source=source, timestamp=now,
                    ))
        return results

    def _extract_visit(self, text: str, source: SignalSource, now: datetime) -> list[Signal]:
        results = []
        text_lower = text.lower()
        for keyword, (category, subtype) in PLACE_TYPES.items():
            if keyword in text_lower:
                results.append(Signal(
                    raw_text=text, signal_type=SignalType.VISIT,
                    extracted_value=keyword, confidence=0.75, source=source, timestamp=now,
                    place_type=category, place_subtype=subtype,
                ))
        return results

    async def _llm_extract(self, text: str, source: SignalSource, now: datetime) -> list[Signal]:
        if not self._llm:
            return []
        prompt = (
            "Extract socioeconomic signals from this text. Reply with JSON array of objects with fields: "
            "signal_type (location/school/profession/visit/language/family), extracted_value, confidence (0-1).\n\n"
            f"Text: {text}\n\nJSON:"
        )
        try:
            import json
            resp = await self._llm.complete(prompt, temperature=0.1)
            resp = resp.strip().strip("```json").strip("```").strip()
            data = json.loads(resp)
            return [
                Signal(
                    raw_text=text,
                    signal_type=SignalType(item.get("signal_type", "generic")),
                    extracted_value=str(item.get("extracted_value", "")),
                    confidence=float(item.get("confidence", 0.5)),
                    source=source, timestamp=now,
                )
                for item in data
                if item.get("extracted_value")
            ]
        except Exception as exc:
            logger.debug("LLM extraction failed: %s", exc)
            return []
