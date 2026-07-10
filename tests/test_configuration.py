from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from sociomemory import Sociomemory
from sociomemory.config import SociomemoryConfig
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.models.signals import Signal, SignalType
from sociomemory.privacy.consent import ConsentScope
from sociomemory.storage.graph_backend import GraphBackend


def test_config_validation_has_no_filesystem_side_effect(tmp_path):
    data_dir = tmp_path / "not-created"

    config = SociomemoryConfig(data_dir=data_dir, llm_backend="NONE", country="in")

    assert config.llm_backend == "none"
    assert config.country == "IN"
    assert not data_dir.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("llm_backend", "unsupported"),
        ("embedding_dim", 0),
        ("enrichment_cache_ttl_hours", 0),
        ("country", "India"),
    ],
)
def test_config_rejects_invalid_values(field, value):
    with pytest.raises(ValueError):
        SociomemoryConfig(**{field: value})


def test_models_normalize_naive_datetimes_to_utc():
    node = Node(child_id="child", type=NodeType.CHILD)
    signal = Signal(raw_text="x", signal_type=SignalType.GENERIC, extracted_value="x")

    assert node.created_at.tzinfo == UTC
    assert signal.timestamp.tzinfo == UTC


def test_opt_in_consent_enforcement_fails_closed(tmp_path):
    memory = Sociomemory(
        SociomemoryConfig(data_dir=tmp_path, llm_backend="none", enforce_consent=True)
    )

    with pytest.raises(PermissionError):
        memory._require_signal_consent("child", SignalType.LOCATION)

    memory.privacy.record_consent("child", "parent", ConsentScope.LOCATION_AREA)
    memory._require_signal_consent("child", SignalType.LOCATION)
    memory._cache.close()
    memory._consent.close()


@pytest.mark.asyncio
async def test_sociomemory_accepts_custom_graph_backend(tmp_path):
    backend = MagicMock(spec=GraphBackend)
    backend.connect = AsyncMock()
    backend.init_schema = AsyncMock()
    backend.close = AsyncMock()
    memory = Sociomemory(
        SociomemoryConfig(data_dir=tmp_path, llm_backend="none"),
        graph_backend=backend,
    )

    await memory.connect()
    await memory.close()

    assert memory._backend is backend
    backend.connect.assert_awaited_once()
    backend.init_schema.assert_awaited_once()
    backend.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_without_llm_returns_warning(tmp_path):
    memory = Sociomemory(SociomemoryConfig(data_dir=tmp_path, llm_backend="none"))

    result = await memory.ingest("child", "hum Koramangala mein rehte hain")

    assert result["status"] == "no_signals"
    assert "LLM is not configured" in result["warnings"][0]
    memory._cache.close()
    memory._consent.close()
