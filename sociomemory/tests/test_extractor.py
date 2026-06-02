from __future__ import annotations

import pytest

from sociomemory.pipeline.extractor import SignalExtractor
from sociomemory.models.signals import SignalType


@pytest.mark.asyncio
async def test_extract_location():
    extractor = SignalExtractor()
    signals = await extractor.extract("I live in Koramangala, Bangalore")
    assert any(s.signal_type == SignalType.LOCATION for s in signals)
    loc = next(s for s in signals if s.signal_type == SignalType.LOCATION)
    assert "koramangala" in loc.extracted_value.lower()


@pytest.mark.asyncio
async def test_extract_iskcon_visit():
    extractor = SignalExtractor()
    signals = await extractor.extract("We went to ISKCON temple last Sunday")
    visit_sigs = [s for s in signals if s.signal_type == SignalType.VISIT]
    assert len(visit_sigs) > 0
    subtypes = [s.place_subtype for s in visit_sigs]
    assert "iskcon" in subtypes


@pytest.mark.asyncio
async def test_extract_school():
    extractor = SignalExtractor()
    signals = await extractor.extract("She goes to DPS Bangalore School")
    school_sigs = [s for s in signals if s.signal_type == SignalType.SCHOOL]
    assert len(school_sigs) > 0


@pytest.mark.asyncio
async def test_extract_mountain_visit():
    extractor = SignalExtractor()
    signals = await extractor.extract("We went to the mountain for a picnic last weekend")
    visit_sigs = [s for s in signals if s.signal_type == SignalType.VISIT]
    assert any(s.place_type == "mountain" for s in visit_sigs)


@pytest.mark.asyncio
async def test_no_signals_empty_text():
    extractor = SignalExtractor()
    signals = await extractor.extract("Hello how are you today")
    assert signals == []
