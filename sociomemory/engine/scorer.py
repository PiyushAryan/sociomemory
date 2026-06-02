from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sociomemory.graph.nodes import Node, NodeType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph

logger = logging.getLogger(__name__)

NODE_RELEVANCE_WEIGHTS: dict[NodeType, float] = {
    NodeType.CHILD: 1.0,
    NodeType.IMPLICATION: 1.0,
    NodeType.THERAPY_OPPORTUNITY: 0.9,
    NodeType.TRADEOFF: 0.9,
    NodeType.INCOME: 0.85,
    NodeType.SAFETY: 0.8,
    NodeType.SCHOOL: 0.75,
    NodeType.TRANSPORT: 0.75,
    NodeType.RELIGIOUS: 0.7,
    NodeType.LIFESTYLE: 0.7,
    NodeType.SENSORY_EVIDENCE: 0.7,
    NodeType.CULTURAL: 0.65,
    NodeType.ECONOMIC: 0.65,
    NodeType.EMPLOYER: 0.6,
    NodeType.VISIT: 0.6,
    NodeType.NEIGHBORHOOD: 0.5,
    NodeType.PARENT: 0.5,
    NodeType.REAL_ESTATE: 0.5,
    NodeType.PLACE: 0.4,
    NodeType.SIGNAL: 0.3,
}


class RelevanceScorer:

    def __init__(self, graph: "MemoryGraph"):
        self._graph = graph

    def score_node(self, node: Node) -> float:
        type_weight = NODE_RELEVANCE_WEIGHTS.get(node.type, 0.4)
        stale_penalty = 0.5 if node.stale else 0.0
        return round(type_weight * node.confidence * (1.0 - stale_penalty), 3)

    def rank_nodes(self, nodes: list[Node], top_k: int = 20) -> list[Node]:
        scored = sorted(nodes, key=self.score_node, reverse=True)
        return scored[:top_k]

    async def get_top_coaching_nodes(self, top_k: int = 20) -> list[Node]:
        from sociomemory.graph import cypher as Q
        records = await self._graph._neo4j.run(Q.GET_ALL_NODES, child_id=self._graph.child_id)
        nodes = [self._graph._parse_node(r["n"]) for r in records if r.get("n")]
        return self.rank_nodes(nodes, top_k=top_k)
