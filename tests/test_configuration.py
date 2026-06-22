from __future__ import annotations

from datetime import UTC

import pytest

from sociomemory import Sociomemory
from sociomemory.config import SociomemoryConfig
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.models.signals import Signal, SignalType
from sociomemory.privacy.consent import ConsentScope


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
