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
async def test_llm_bad_json_preserves_lane_a(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM("not json at all")
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("we went to the temple today")
    # Lane A visit survives the bad-JSON LLM path...
    assert any(s.signal_type == SignalType.VISIT for s in signals)
    # ...and no fabricated LOCATION comes from the junk output.
    assert all(s.signal_type != SignalType.LOCATION for s in signals)


@pytest.mark.asyncio
async def test_llm_malformed_place_type_does_not_raise(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM(
        '[{"value": "beach", "signal_type": "visit", "confidence": 0.8, "place_type": ["beach"]}]'
    )
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("random text")  # must not raise
    assert all(not isinstance(s.place_type, list) for s in signals)


@pytest.mark.asyncio
async def test_confidence_clamped():
    llm = FakeLLM('[{"value": "Pune", "signal_type": "location", "confidence": 5}]')
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("Pune")
    loc = next(s for s in signals if s.signal_type == SignalType.LOCATION)
    assert loc.confidence == 1.0


@pytest.mark.asyncio
async def test_no_llm_ignores_spacy_candidates(monkeypatch):
    from sociomemory.pipeline import extractor as ex
    from sociomemory.pipeline.ner import Candidate

    monkeypatch.setattr(
        ex, "spacy_candidates", lambda text: [Candidate("Koramangala", "GPE", 0, 11)]
    )
    extractor = SignalExtractor()  # no LLM
    signals = await extractor.extract("Koramangala")
    assert signals == []


@pytest.mark.asyncio
async def test_no_spacy_no_llm_yields_only_visits(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    extractor = SignalExtractor()  # no LLM
    assert await extractor.extract("hum Koramangala mein rehte hain") == []
    visits = await extractor.extract("We went to ISKCON temple")
    assert any(s.signal_type == SignalType.VISIT for s in visits)


@pytest.mark.asyncio
async def test_llm_failure_does_not_fall_back_to_label_heuristic(monkeypatch):
    from sociomemory.pipeline import extractor as ex
    from sociomemory.pipeline.ner import Candidate

    monkeypatch.setattr(
        ex, "spacy_candidates", lambda text: [Candidate("Koramangala", "GPE", 0, 11)]
    )

    class BadLLM(FakeLLM):
        async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
            raise RuntimeError("boom")

    extractor = SignalExtractor(llm=BadLLM(""))
    signals = await extractor.extract("Koramangala")
    assert signals == []


@pytest.mark.asyncio
async def test_iskcon_subtype_preserved_with_llm(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM(
        '[{"value":"temple","signal_type":"visit","confidence":0.95,"place_type":"temple"}]'
    )
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("We went to ISKCON temple")
    visits = [s for s in signals if s.signal_type == SignalType.VISIT and s.place_type == "temple"]
    assert len(visits) == 1
    assert visits[0].place_subtype == "iskcon"


@pytest.mark.asyncio
async def test_llm_place_type_normalized_via_place_types(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM(
        '[{"value":"iskcon","signal_type":"visit","confidence":0.9,"place_type":"iskcon"}]'
    )
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("random text with no place keyword")
    visits = [s for s in signals if s.signal_type == SignalType.VISIT]
    assert len(visits) == 1
    assert visits[0].place_type == "temple" and visits[0].place_subtype == "iskcon"


@pytest.mark.asyncio
async def test_llm_discovers_non_keyword_visit(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM(
        '[{"value":"Golconda Fort","signal_type":"visit","confidence":0.8,"place_type":"fort"}]'
    )
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("we saw Golconda Fort yesterday")
    assert any(s.signal_type == SignalType.VISIT and s.place_type == "fort" for s in signals)


@pytest.mark.asyncio
async def test_llm_extracts_named_venue_visit_without_keyword(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM(
        '[{"value":"Blue Lantern Diner","signal_type":"visit",'
        '"confidence":0.88,"place_type":"restaurant"}]'
    )
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("I went to Blue Lantern Diner today")
    visits = [s for s in signals if s.signal_type == SignalType.VISIT]
    assert len(visits) == 1
    assert visits[0].extracted_value == "Blue Lantern Diner"
    assert visits[0].place_type == "restaurant"


@pytest.mark.asyncio
async def test_llm_prompt_requests_named_venues_and_proper_nouns(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM("[]")
    extractor = SignalExtractor(llm=llm)
    await extractor.extract("I went to a named venue today")
    prompt = llm.calls[0]
    assert "named venues" in prompt
    assert "Preserve exact proper nouns" in prompt
    assert "restaurants, cafes, parks" in prompt


@pytest.mark.asyncio
async def test_llm_handles_json_code_fence(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    payload = '```json\n[{"value": "Pune", "signal_type": "location", "confidence": 0.9}]\n```'
    llm = FakeLLM(payload)
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("x")
    assert any(
        s.signal_type == SignalType.LOCATION and s.extracted_value == "Pune" for s in signals
    )


@pytest.mark.asyncio
async def test_llm_signal_type_case_insensitive(monkeypatch):
    from sociomemory.pipeline import extractor as ex

    monkeypatch.setattr(ex, "spacy_candidates", lambda text: [])
    llm = FakeLLM('[{"value": "Pune", "signal_type": "LOCATION", "confidence": 0.9}]')
    extractor = SignalExtractor(llm=llm)
    signals = await extractor.extract("x")
    assert any(s.signal_type == SignalType.LOCATION for s in signals)
