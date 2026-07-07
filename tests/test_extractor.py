from __future__ import annotations

import pytest

from sociomemory.models.signals import SignalType
from sociomemory.pipeline.extractor import SignalExtractor


class FakeLLM:
    """Minimal BaseLLM stub that returns a canned completion payload."""

    def __init__(self, payload: str):
        self._payload = payload
        self.calls: list[str] = []

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        self.calls.append(prompt)
        return self._payload

    async def embed(self, text: str) -> list[float]:
        return []

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_iskcon_visit_still_works_offline():
    # Lane A (PLACE_TYPES) requires neither spaCy nor an LLM.
    extractor = SignalExtractor()
    signals = await extractor.extract("We went to ISKCON temple last Sunday")
    visit_sigs = [s for s in signals if s.signal_type == SignalType.VISIT]
    assert any(s.place_subtype == "iskcon" for s in visit_sigs)


@pytest.mark.asyncio
async def test_mountain_visit_still_works_offline():
    extractor = SignalExtractor()
    signals = await extractor.extract("We went to the mountain for a picnic last weekend")
    assert any(s.place_type == "mountain" for s in signals if s.signal_type == SignalType.VISIT)


@pytest.mark.asyncio
async def test_llm_types_codemixed_location():
    llm = FakeLLM('[{"value": "Koramangala", "signal_type": "location", "confidence": 0.9}]')
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("hum Koramangala mein rehte hain")
    assert any(
        s.signal_type == SignalType.LOCATION and "koramangala" in s.extracted_value.lower()
        for s in signals
    )


@pytest.mark.asyncio
async def test_llm_types_codemixed_school():
    llm = FakeLLM('[{"value": "DPS", "signal_type": "school", "confidence": 0.85}]')
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("beta DPS mein padhta hai")
    assert any(s.signal_type == SignalType.SCHOOL for s in signals)


@pytest.mark.asyncio
async def test_llm_visit_dedupes_with_lane_a():
    # "beach" is a PLACE_TYPES keyword (Lane A) AND emitted by the LLM (Lane C).
    llm = FakeLLM(
        '[{"value": "beach", "signal_type": "visit", "confidence": 0.9, "place_type": "beach"}]'
    )
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("hum kal beach gaye the")
    beach = [s for s in signals if s.signal_type == SignalType.VISIT and s.place_type == "beach"]
    assert len(beach) == 1
    assert beach[0].confidence == 0.9  # higher-confidence entry wins


@pytest.mark.asyncio
async def test_llm_bad_json_returns_lane_a_only(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    # Force no spaCy candidates so bad JSON has no label-heuristic fallback input.
    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM("not json at all")
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("hum Koramangala mein rehte hain")
    assert all(s.signal_type != SignalType.LOCATION for s in signals)


@pytest.mark.asyncio
async def test_confidence_clamped():
    llm = FakeLLM('[{"value": "Pune", "signal_type": "location", "confidence": 5}]')
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("Pune")
    loc = next(s for s in signals if s.signal_type == SignalType.LOCATION)
    assert loc.confidence == 1.0
