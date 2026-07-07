from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sociomemory.models.signals import Signal, SignalSource, SignalType
from sociomemory.pipeline.ner import Candidate, spacy_candidates
from sociomemory.time import utc_now

if TYPE_CHECKING:
    from sociomemory.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# keyword -> (place_type, place_subtype). place_type is the SPECIFIC type that
# the builder, behavioral inference, and temporal pattern detection key on;
# place_subtype carries the refinement (e.g. an ISKCON temple).
PLACE_TYPES = {
    "iskcon": ("temple", "iskcon"),
    "temple": ("temple", None),
    "mosque": ("mosque", None),
    "church": ("church", None),
    "gurudwara": ("gurudwara", None),
    "park": ("park", None),
    "playground": ("playground", None),
    "mall": ("mall", None),
    "museum": ("museum", None),
    "zoo": ("zoo", None),
    "beach": ("beach", None),
    "mountain": ("mountain", None),
    "hill station": ("hill_station", None),
    "water park": ("water_park", None),
    "snow park": ("snow_park", None),
    "library": ("library", None),
    "metro station": ("metro_station", None),
    "metro": ("metro_station", None),
    "railway station": ("railway_station", None),
    "bus stand": ("bus_stand", None),
    "airport": ("airport", None),
    "restaurant": ("restaurant", None),
    "cafe": ("cafe", None),
    "hospital": ("hospital", None),
    "clinic": ("clinic", None),
    "market": ("market", None),
    "supermarket": ("supermarket", None),
    "stadium": ("stadium", None),
    "cinema": ("cinema", None),
    "theatre": ("theatre", None),
    "theater": ("theatre", None),
    "aquarium": ("aquarium", None),
}

# Degraded mode only (spaCy present, LLM absent): map ONLY unambiguous labels.
# ORG (school vs employer), PERSON (parent vs teacher vs friend), and NORP
# (nationality vs religion) are deliberately excluded — guessing their role
# without the LLM plants wrong signals.
_LABEL_MAP = {
    "GPE": SignalType.LOCATION,
    "LOC": SignalType.LOCATION,
    "LANGUAGE": SignalType.LANGUAGE,
}

_DEGRADED_CONFIDENCE = 0.6


class SignalExtractor:
    def __init__(self, llm: BaseLLM | None = None):
        self._llm = llm

    async def extract(
        self, text: str, source: SignalSource = SignalSource.CONVERSATION
    ) -> list[Signal]:
        now = utc_now()
        signals: list[Signal] = []
        # Lane A: offline place/visit keyword scan.
        signals.extend(self._extract_visit(text, source, now))
        # Lane B: optional spaCy candidate hints.
        candidates = spacy_candidates(text)
        # Lane C: LLM discovery + typing (primary), or degraded label heuristic.
        if self._llm:
            signals.extend(await self._llm_type_entities(text, candidates, source, now))
        else:
            signals.extend(self._label_heuristic(candidates, text, source, now))
        return self._dedup(signals)

    def _extract_visit(self, text: str, source: SignalSource, now: datetime) -> list[Signal]:
        text_lower = text.lower()
        by_type: dict[str, Signal] = {}
        for keyword, (place_type, subtype) in PLACE_TYPES.items():
            if keyword not in text_lower:
                continue
            existing = by_type.get(place_type)
            if existing is not None and existing.place_subtype and subtype is None:
                continue
            by_type[place_type] = Signal(
                raw_text=text,
                signal_type=SignalType.VISIT,
                extracted_value=keyword,
                confidence=0.75,
                source=source,
                timestamp=now,
                place_type=place_type,
                place_subtype=subtype,
            )
        return list(by_type.values())

    async def _llm_type_entities(
        self,
        text: str,
        candidates: list[Candidate],
        source: SignalSource,
        now: datetime,
    ) -> list[Signal]:
        hints = ", ".join(sorted({c.text for c in candidates})) or "(none)"
        types = "/".join(t.value for t in SignalType)
        system = (
            "You extract socioeconomic signals about a child and family from short, "
            "often code-mixed (Hindi/English) text. Reply with ONLY a JSON array."
        )
        prompt = (
            f"Candidate entities already detected: {hints}\n"
            "Classify each candidate that is a socioeconomic signal, AND add any "
            "signals present in the text that are not in the candidate list.\n"
            f'Each object: {{"value": str, "signal_type": one of [{types}], '
            '"confidence": 0-1, "place_type": optional str for visits}}.\n'
            "Omit anything that is not a real signal.\n\n"
            f"Text: {text}\n\nJSON:"
        )
        try:
            resp = await self._llm.complete(prompt, system=system, temperature=0.1)
            data = json.loads(self._strip_fences(resp))
        except Exception as exc:
            logger.debug("LLM typing failed: %s", exc)
            return self._label_heuristic(candidates, text, source, now)
        if not isinstance(data, list):
            return []
        return [
            self._signal_from_item(item, text, source, now)
            for item in data
            if self._valid_item(item)
        ]

    def _label_heuristic(
        self,
        candidates: list[Candidate],
        text: str,
        source: SignalSource,
        now: datetime,
    ) -> list[Signal]:
        out: list[Signal] = []
        for cand in candidates:
            signal_type = _LABEL_MAP.get(cand.label)
            if signal_type is None:
                continue
            out.append(
                Signal(
                    raw_text=text,
                    signal_type=signal_type,
                    extracted_value=cand.text,
                    confidence=_DEGRADED_CONFIDENCE,
                    source=source,
                    timestamp=now,
                )
            )
        return out

    @staticmethod
    def _strip_fences(resp: str) -> str:
        resp = resp.strip()
        if resp.startswith("```"):
            resp = resp.split("\n", 1)[-1] if "\n" in resp else resp[3:]
            if resp.rstrip().endswith("```"):
                resp = resp.rstrip()[:-3]
        return resp.strip()

    @staticmethod
    def _valid_item(item) -> bool:
        if not isinstance(item, dict):
            return False
        value = str(item.get("value", "")).strip()
        return bool(value) and item.get("signal_type") in SignalType._value2member_map_

    @staticmethod
    def _signal_from_item(item: dict, text: str, source: SignalSource, now: datetime) -> Signal:
        signal_type = SignalType(item["signal_type"])
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.6))))
        except (TypeError, ValueError):
            confidence = 0.6
        place_type = item.get("place_type") if signal_type == SignalType.VISIT else None
        return Signal(
            raw_text=text,
            signal_type=signal_type,
            extracted_value=str(item["value"]).strip(),
            confidence=confidence,
            source=source,
            timestamp=now,
            place_type=place_type,
        )

    @staticmethod
    def _dedup(signals: list[Signal]) -> list[Signal]:
        best: dict[tuple[SignalType, str], Signal] = {}
        for signal in signals:
            if signal.signal_type == SignalType.VISIT:
                key_value = (signal.place_type or signal.extracted_value or "").lower()
            else:
                key_value = (signal.extracted_value or "").strip().lower()
            key = (signal.signal_type, key_value)
            current = best.get(key)
            if current is None:
                best[key] = signal
            elif signal.confidence > current.confidence:
                best[key] = signal
            elif (
                signal.confidence == current.confidence
                and signal.place_subtype
                and not current.place_subtype
            ):
                best[key] = signal
        return list(best.values())
