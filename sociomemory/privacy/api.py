from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sociomemory.privacy.consent import ConsentManager, ConsentScope
from sociomemory.storage.paths import storage_key

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.storage.graph_backend import GraphBackend

logger = logging.getLogger(__name__)


class PrivacyAPI:
    """Consent and deletion operations exposed by :class:`Sociomemory`."""

    def __init__(
        self,
        consent: ConsentManager,
        backend: GraphBackend,
        graphs: dict[str, MemoryGraph],
        faiss_dir: Path,
        keyword_dir: Path,
    ) -> None:
        self._consent = consent
        self._backend = backend
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
        await self._backend.erase_child(child_id)
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
        nodes = [node.to_storage_props() for node in await self._backend.get_all_nodes(child_id)]
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
