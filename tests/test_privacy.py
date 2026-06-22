from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sociomemory.privacy.api import PrivacyAPI
from sociomemory.privacy.consent import ConsentManager, ConsentScope
from sociomemory.storage.paths import storage_key


def test_storage_key_preserves_safe_ids_and_hashes_paths():
    assert storage_key("child_001") == "child_001"
    unsafe = storage_key("../../outside")
    assert unsafe.startswith("child-")
    assert "/" not in unsafe and ".." not in unsafe


@pytest.mark.asyncio
async def test_erase_evicts_cached_graph_and_revokes_consent(tmp_path):
    consent = ConsentManager(str(tmp_path / "consent.db"))
    consent.record_consent("child", "parent", ConsentScope.EXPORT)
    neo4j = MagicMock()
    neo4j.run_write = AsyncMock(return_value=[])
    graph = MagicMock()
    graphs = {"child": graph}
    privacy = PrivacyAPI(consent, neo4j, graphs, tmp_path / "faiss", tmp_path / "keyword")

    await privacy.erase("child")

    graph.delete_local_indexes.assert_called_once_with()
    assert "child" not in graphs
    assert not consent.check_consent("child", ConsentScope.EXPORT)
    consent.close()


@pytest.mark.asyncio
async def test_erase_uses_safe_local_paths_when_graph_is_not_cached(tmp_path):
    faiss_dir = tmp_path / "faiss"
    keyword_dir = tmp_path / "keyword"
    faiss_dir.mkdir()
    keyword_dir.mkdir()
    child_id = "../../outside"
    key = storage_key(child_id)
    files = [
        faiss_dir / f"{key}.faiss",
        faiss_dir / f"{key}.map.json",
        keyword_dir / f"{key}.bm25.json",
    ]
    for path in files:
        path.write_text("data")

    consent = ConsentManager(str(tmp_path / "consent.db"))
    neo4j = MagicMock()
    neo4j.run_write = AsyncMock(return_value=[])
    privacy = PrivacyAPI(consent, neo4j, {}, faiss_dir, keyword_dir)

    await privacy.erase(child_id)

    assert not any(path.exists() for path in files)
    consent.close()


def test_require_consent_raises_for_missing_scope(tmp_path):
    consent = ConsentManager(str(tmp_path / "consent.db"))
    privacy = PrivacyAPI(consent, MagicMock(), {}, tmp_path, tmp_path)

    with pytest.raises(PermissionError):
        privacy.require_consent("child", ConsentScope.INCOME_INFERENCE)
    consent.close()


@pytest.mark.asyncio
async def test_export_data_requires_consent_and_returns_nodes(tmp_path):
    consent = ConsentManager(str(tmp_path / "consent.db"))
    consent.record_consent("child", "parent", ConsentScope.EXPORT)
    neo4j = MagicMock()
    neo4j.run = AsyncMock(return_value=[{"n": {"id": "node-1", "child_id": "child"}}])
    privacy = PrivacyAPI(consent, neo4j, {}, tmp_path, tmp_path)

    exported = await privacy.export_data("child")

    assert exported["nodes"] == [{"id": "node-1", "child_id": "child"}]
    consent.close()
