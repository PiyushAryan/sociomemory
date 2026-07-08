from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.nodes import Node, NodeType


@dataclass
class GraphSnapshot:
    """Backend-neutral graph data returned by traversal and export operations."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class GraphBackend(Protocol):
    """Storage port implemented by each supported graph database adapter."""

    async def connect(self) -> None: ...

    async def init_schema(self) -> None: ...

    async def close(self) -> None: ...

    async def health_check(self) -> bool: ...

    async def merge_node(self, node: Node) -> None: ...

    async def update_node_properties(
        self,
        node_id: str,
        child_id: str,
        node_type: NodeType,
        properties: dict[str, Any],
    ) -> None: ...

    async def merge_edge(self, edge: Edge) -> None: ...

    async def merge_subgraph(self, nodes: list[Node], edges: list[Edge]) -> None: ...

    async def traverse(
        self,
        start_id: str,
        child_id: str,
        edge_types: list[EdgeType] | None,
        max_depth: int,
        min_confidence: float,
        limit: int,
    ) -> GraphSnapshot: ...

    async def shortest_path(self, source_id: str, target_id: str) -> list[str]: ...

    async def neighborhood(self, node_id: str, child_id: str, radius: int) -> GraphSnapshot: ...

    async def find_inference_chains(
        self, child_id: str, from_type: NodeType, to_type: NodeType
    ) -> list[dict[str, Any]]: ...

    async def find_contradictions(self, child_id: str) -> list[tuple[Node, Node, float]]: ...

    async def get_nodes_by_type(self, child_id: str, node_type: NodeType) -> list[Node]: ...

    async def get_node(self, node_id: str) -> Node | None: ...

    async def get_all_nodes(self, child_id: str) -> list[Node]: ...

    async def coaching_subgraph(self, child_node_id: str, child_id: str) -> GraphSnapshot: ...

    async def query_by_event_date(
        self,
        child_id: str,
        start: datetime,
        end: datetime,
        node_type: NodeType | None,
    ) -> list[Node]: ...

    async def get_timeline(self, child_id: str) -> list[Node]: ...

    async def get_provenance(self, node_id: str, child_id: str) -> list[dict[str, Any]]: ...

    async def mark_stale(self, node_id: str) -> int: ...

    async def get_stale_nodes(self, child_id: str) -> list[Node]: ...

    async def compute_convergence(self, node_id: str) -> float: ...

    async def node_count(self, child_id: str) -> int: ...

    async def edge_count(self, child_id: str) -> int: ...

    async def erase_child(self, child_id: str) -> None: ...

    async def list_children(self, limit: int = 100) -> list[str]: ...

    async def export_graph(
        self,
        child_id: str,
        start_id: str | None = None,
        max_depth: int = 3,
        min_confidence: float = 0.0,
        limit: int = 200,
    ) -> GraphSnapshot: ...
