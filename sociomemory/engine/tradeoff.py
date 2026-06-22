from __future__ import annotations

import logging
from itertools import combinations
from typing import TYPE_CHECKING

from sociomemory.graph.nodes import NodeType
from sociomemory.models.coaching import TradeOff

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class TradeOffDetector:
    def __init__(self, graph: MemoryGraph, llm: BaseLLM | None = None):
        self._graph = graph
        self._llm = llm

    async def detect(self) -> list[TradeOff]:
        tradeoffs = []

        contradictions = await self._graph.find_contradictions()
        for node_a, node_b, tension in contradictions:
            tradeoffs.append(
                TradeOff(
                    dimension=self._infer_dimension(node_a, node_b),
                    positive_node_id=node_a.id,
                    negative_node_id=node_b.id,
                    positive_summary=str(node_a.properties),
                    negative_summary=str(node_b.properties),
                    tension_score=tension,
                )
            )

        impl_nodes = await self._graph.get_nodes_by_type(NodeType.IMPLICATION)
        for a, b in combinations(impl_nodes, 2):
            a_dim = a.properties.get("dimension", "")
            b_dim = b.properties.get("dimension", "")
            a_dir = a.properties.get("direction", "")
            b_dir = b.properties.get("direction", "")
            if a_dim and a_dim == b_dim and a_dir and b_dir and a_dir != b_dir:
                pos = a if a_dir == "positive" else b
                neg = b if a_dir == "positive" else a
                tradeoffs.append(
                    TradeOff(
                        dimension=a_dim,
                        positive_node_id=pos.id,
                        negative_node_id=neg.id,
                        positive_summary=pos.properties.get("text", ""),
                        negative_summary=neg.properties.get("text", ""),
                        tension_score=0.6,
                    )
                )

        if self._llm:
            for to in tradeoffs:
                if not to.resolution:
                    to.resolution = await self._resolve(to)

        return tradeoffs

    def _infer_dimension(self, a, b) -> str:
        a_type = a.type.value.lower()
        b_type = b.type.value.lower()
        if "safety" in a_type or "safety" in b_type:
            return "outdoor_safety"
        if "economic" in a_type or "income" in a_type:
            return "affordability"
        if "transport" in a_type:
            return "accessibility"
        return "general"

    async def _resolve(self, tradeoff: TradeOff) -> str:
        if self._llm is None:
            return ""
        prompt = (
            f"A child's coaching context has a trade-off on '{tradeoff.dimension}'.\n"
            f"Positive: {tradeoff.positive_summary}\n"
            f"Negative: {tradeoff.negative_summary}\n"
            f"Provide a 1-2 sentence practical coaching resolution."
        )
        return await self._llm.complete(prompt, temperature=0.3)
