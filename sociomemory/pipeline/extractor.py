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

_VALID_SIGNAL_VALUES = {t.value for t in SignalType}


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
        if text.strip() and self._llm:
            # spaCy candidates are only hints for LLM typing; they are not used as a
            # standalone degraded extraction mode.
            candidates = spacy_candidates(text)
            signals.extend(await self._llm_type_entities(text, candidates, source, now))
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
        llm = self._llm
        if llm is None:
            return []
        hints = ", ".join(sorted({c.text for c in candidates})) or "(none)"
        types = "/".join(t.value for t in SignalType)
        system = (
            "You extract durable memory signals about a child and family from short, "
            "often code-mixed (Hindi/English) text. Reply with ONLY a JSON array."
        )
        prompt = (
            f"Candidate entities already detected: {hints}\n"
            "Classify each candidate that is a useful memory signal, AND add any "
            "signals present in the text that are not in the candidate list.\n"
            "Extract explicit visits to named venues and public places as visit signals. "
            "This includes restaurants, cafes, parks, malls, schools, workplaces, "
            "religious places, transit points, attractions, hospitals, clinics, and "
            "other named places. Preserve exact proper nouns for venue, brand, company, "
            "school, workplace, and locality names.\n"
            "For visits, set value to the exact mentioned place name and set place_type "
            "to a generic category such as restaurant, cafe, park, mall, school, "
            "workplace, public_place, attraction, transit, hospital, clinic, religious_place, "
            "or unknown_place. Do not require the category to appear in a fixed list.\n"
            f'Each object: {{"value": str, "signal_type": one of [{types}], '
            '"confidence": 0-1, "place_type": optional str for visits}}.\n'
            "Omit anything that is not a real signal.\n\n"
            f"Text: {text}\n\nJSON:"
        )
        try:
            resp = await llm.complete(prompt, system=system, temperature=0.1)
            data = json.loads(self._strip_fences(resp))
        except Exception as exc:
            logger.debug("LLM typing failed: %s", exc)
            return []
        if not isinstance(data, list):
            # Parseable but off-contract shape: not a failure — Lane A signals still stand.
            return []
        signals: list[Signal] = []
        for item in data:
            if not self._valid_item(item):
                continue
            try:
                signals.append(self._signal_from_item(item, text, source, now))
            except Exception as exc:  # malformed field types from the LLM
                logger.debug("skipping malformed LLM item %r: %s", item, exc)
        return signals

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
        signal_type = str(item.get("signal_type", "")).strip().lower()
        return bool(value) and signal_type in _VALID_SIGNAL_VALUES

    @staticmethod
    def _signal_from_item(item: dict, text: str, source: SignalSource, now: datetime) -> Signal:
        signal_type = SignalType(str(item["signal_type"]).strip().lower())
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.6))))
        except (TypeError, ValueError):
            confidence = 0.6
        place_type: str | None = None
        place_subtype: str | None = None
        if signal_type == SignalType.VISIT:
            raw_place = item.get("place_type")
            if isinstance(raw_place, str) and raw_place.strip():
                mapped = PLACE_TYPES.get(raw_place.strip().lower())
                if mapped:
                    place_type, place_subtype = mapped
                else:
                    place_type = raw_place.strip()
        return Signal(
            raw_text=text,
            signal_type=signal_type,
            extracted_value=str(item["value"]).strip(),
            confidence=confidence,
            source=source,
            timestamp=now,
            place_type=place_type,
            place_subtype=place_subtype,
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
                if (
                    signal.signal_type == SignalType.VISIT
                    and current.place_subtype
                    and not signal.place_subtype
                ):
                    signal = signal.model_copy(update={"place_subtype": current.place_subtype})
                best[key] = signal
            elif (
                signal.confidence == current.confidence
                and signal.place_subtype
                and not current.place_subtype
            ):
                best[key] = signal
        return list(best.values())
