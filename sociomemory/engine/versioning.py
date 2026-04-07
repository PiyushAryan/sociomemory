from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sociomemory.graph.edges import EdgeType
from sociomemory.graph.nodes import Node, NodeType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph

logger = logging.getLogger(__name__)


class VersioningEngine:
    """
    Manages UPDATES / EXTENDS / DERIVES relationships.
    When a node is UPDATED, all DERIVES descendants are cascade-staled.
    """

    def __init__(self, graph: "MemoryGraph"):
        self._graph = graph

    async def update_node(self, old_node_id: str, new_node: Node) -> None:
        """Merge new_node, create UPDATES edge new→old, cascade-stale descendants."""
        await self._graph.merge_subgraph([new_node], [])
        from sociomemory.graph.edges import Edge
        updates_edge = Edge(
            source_id=new_node.id,
            target_id=old_node_id,
            type=EdgeType.UPDATES,
            weight=1.0,
            properties={"updated_at": datetime.utcnow().isoformat()},
        )
        await self._graph.merge_subgraph([], [updates_edge])
        count = await self._graph.mark_stale(old_node_id)
        logger.info("Updated %s → %d downstream nodes staled", old_node_id, count)

    async def extend_node(self, base_node_id: str, new_node: Node) -> None:
        """Record that new_node EXTENDS base_node (adds detail without contradiction)."""
        await self._graph.merge_subgraph([new_node], [])
        from sociomemory.graph.edges import Edge
        extends_edge = Edge(
            source_id=new_node.id,
            target_id=base_node_id,
            type=EdgeType.EXTENDS,
            weight=1.0,
        )
        await self._graph.merge_subgraph([], [extends_edge])

    async def recompute_stale(self) -> list[str]:
        """Return IDs of all stale nodes in topological order for recomputation."""
        stale_nodes = await self._graph.get_stale_nodes()
        priority_order = [
            NodeType.REAL_ESTATE, NodeType.ECONOMIC, NodeType.TRANSPORT,
            NodeType.SAFETY, NodeType.CULTURAL, NodeType.INCOME, NodeType.IMPLICATION,
        ]

        def sort_key(node: Node) -> int:
            try:
                return priority_order.index(node.type)
            except ValueError:
                return len(priority_order)

        stale_nodes.sort(key=sort_key)
        return [n.id for n in stale_nodes]
