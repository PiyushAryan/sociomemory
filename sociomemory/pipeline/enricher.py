from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sociomemory.models.signals import Signal, SignalType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class EnrichmentPipeline:

    def __init__(self, graph: "MemoryGraph", providers: dict[SignalType, list["BaseProvider"]]):
        self._graph = graph
        self._providers = providers

    async def enrich(self, signals: list[Signal]) -> dict[str, Any]:
        results: dict[str, Any] = {"processed": 0, "enriched": 0, "errors": []}
        for signal in signals:
            results["processed"] += 1
            for provider in self._providers.get(signal.signal_type, []):
                try:
                    nodes, edges = await provider.enrich(signal, self._graph)
                    if nodes or edges:
                        await self._graph.merge_subgraph(nodes, edges)
                        results["enriched"] += 1
                except Exception as exc:
                    logger.error("Provider %s error: %s", provider.__class__.__name__, exc)
                    results["errors"].append(str(exc))
        return results
