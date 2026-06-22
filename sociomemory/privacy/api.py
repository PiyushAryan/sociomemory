from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sociomemory.graph import cypher as Q
from sociomemory.privacy.consent import ConsentManager, ConsentScope
from sociomemory.storage.paths import storage_key

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.storage.neo4j_backend import Neo4jBackend

logger = logging.getLogger(__name__)


class PrivacyAPI:
    """Consent and deletion operations exposed by :class:`Sociomemory`."""

    def __init__(
        self,
        consent: ConsentManager,
        neo4j: Neo4jBackend,
        graphs: dict[str, MemoryGraph],
        faiss_dir: Path,
        keyword_dir: Path,
    ) -> None:
        self._consent = consent
        self._neo4j = neo4j
        self._graphs = graphs
        self._faiss_dir = faiss_dir
        self._keyword_dir = keyword_dir

    def record_consent(
        self,
        child_id: str,
        parent_id: str,
        scope: ConsentScope,
        granted: bool = True,
    ) -> None:
        self._consent.record_consent(child_id, parent_id, scope, granted)

    def check_consent(self, child_id: str, scope: ConsentScope) -> bool:
        return self._consent.check_consent(child_id, scope)

    def require_consent(self, child_id: str, scope: ConsentScope) -> None:
        if not self.check_consent(child_id, scope):
            raise PermissionError(f"Consent for {scope.value!r} is required for child {child_id!r}")

    async def erase(self, child_id: str) -> None:
        await self._neo4j.run_write(Q.ERASE_CHILD, child_id=child_id)
        graph = self._graphs.pop(child_id, None)
        if graph is not None:
            graph.delete_local_indexes()
        else:
            self._delete_index_files(child_id)
        self._consent.revoke_all(child_id)
        logger.info("Erased all data for child %s", child_id)

    def export(self, child_id: str) -> dict:
        return {"child_id": child_id, "consents": self._consent.get_all_consents(child_id)}

    async def export_data(self, child_id: str) -> dict:
        self.require_consent(child_id, ConsentScope.EXPORT)
        records = await self._neo4j.run(Q.GET_ALL_NODES, child_id=child_id)
        nodes = []
        for record in records:
            raw = record.get("n")
            properties = getattr(raw, "_properties", None)
            if properties is not None:
                raw = properties
            if isinstance(raw, dict):
                nodes.append(dict(raw))
        return {
            "child_id": child_id,
            "consents": self._consent.get_all_consents(child_id),
            "nodes": nodes,
        }

    def _delete_index_files(self, child_id: str) -> None:
        key = storage_key(child_id)
        for directory, suffixes in (
            (self._faiss_dir, (".faiss", ".map.json")),
            (self._keyword_dir, (".bm25.json",)),
        ):
            for suffix in suffixes:
                path = directory / f"{key}{suffix}"
                if path.exists():
                    path.unlink()
