from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.nodes import DataLevel, Node, NodeType
from sociomemory.time import utc_now

if TYPE_CHECKING:
    from sociomemory.llm.base import BaseLLM
    from sociomemory.storage.graph_backend import GraphBackend
    from sociomemory.storage.keyword import BM25Index
    from sociomemory.storage.vector import VectorIndex

logger = logging.getLogger(__name__)


class Subgraph:
    def __init__(self, nodes: list[Node], edges: list[dict]):
        self.nodes = nodes
        self.edges = edges

    @property
    def node_ids(self) -> list[str]:
        return [n.id for n in self.nodes]

    def get_node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_nodes_by_type(self, node_type: NodeType) -> list[Node]:
        return [n for n in self.nodes if n.type == node_type]

    def aggregate_score(self) -> float:
        if not self.nodes:
            return 0.0
        return sum(n.confidence for n in self.nodes) / len(self.nodes)


class MemoryGraph:
    def __init__(
        self,
        child_id: str,
        backend: GraphBackend,
        faiss: VectorIndex,
        keyword: BM25Index | None = None,
        embedder: BaseLLM | None = None,
    ):
        self.child_id = child_id
        self._backend = backend
        self._faiss = faiss
        self._keyword = keyword
        self._embedder = embedder
        self._child_node_id: str | None = None

    async def add_node(
        self,
        node_type: NodeType,
        properties: dict[str, Any],
        confidence: float = 1.0,
        sensitivity: DataLevel = DataLevel.CONTEXTUAL,
        document_date: datetime | None = None,
        event_date: datetime | None = None,
        source_chunk: str | None = None,
        embedding=None,
    ) -> Node:
        node = Node(
            child_id=self.child_id,
            type=node_type,
            properties=properties,
            confidence=confidence,
            sensitivity=sensitivity,
            document_date=document_date or utc_now(),
            event_date=event_date,
            source_chunk=source_chunk,
        )
        await self._backend.merge_node(node)
        if embedding is not None:
            self._faiss.add(node.id, embedding)
            self._faiss.save()
        self._index_keywords([node])
        return node

    async def update_node_properties(
        self,
        node_id: str,
        node_type: NodeType,
        properties: dict[str, Any],
    ) -> None:
        await self._backend.update_node_properties(
            node_id=node_id,
            child_id=self.child_id,
            node_type=node_type,
            properties=properties,
        )

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
        ttl: datetime | None = None,
    ) -> Edge:
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            weight=weight,
            properties=properties or {},
            ttl=ttl,
        )
        await self._backend.merge_edge(edge)
        return edge

    async def merge_subgraph(self, nodes: list[Node], edges: list[Edge]) -> None:
        await self._backend.merge_subgraph(nodes, edges)
        self._index_keywords(nodes)
        await self._index_embeddings(nodes)

    @staticmethod
    def _node_text(node: Node) -> str:
        label = (
            node.properties.get("name")
            or node.properties.get("title")
            or node.properties.get("value")
            or ""
        )
        detail = " ".join(
            f"{k}={v}"
            for k, v in node.properties.items()
            if k not in {"name", "title", "value"} and isinstance(v, (str, int, float, bool))
        )
        return " ".join(
            part for part in (node.type.value, label, detail, node.source_chunk or "") if part
        ).strip()

    async def _index_embeddings(self, nodes: list[Node]) -> None:
        if not self._embedder or not nodes:
            return
        import numpy as np

        indexed = False
        for node in nodes:
            text = self._node_text(node)
            if not text:
                continue
            try:
                vector = await self._embedder.embed(text)
            except Exception as exc:  # pragma: no cover - provider/network errors
                logger.warning("embedding failed for node %s: %s", node.id, exc)
                continue
            if not vector:
                continue
            self._faiss.add(node.id, np.array(vector, dtype="float32"))
            indexed = True
        if indexed:
            self._faiss.save()

    def _index_keywords(self, nodes: list[Node]) -> None:
        if not self._keyword or not nodes:
            return
        indexed = False
        for node in nodes:
            text = self._node_text(node)
            if not text:
                continue
            self._keyword.add(node.id, text)
            indexed = True
        if indexed:
            self._keyword.save()

    async def traverse(
        self,
        start_id: str,
        edge_types: list[EdgeType] | None = None,
        max_depth: int = 5,
        min_confidence: float = 0.3,
        limit: int = 50,
    ) -> Subgraph:
        snapshot = await self._backend.traverse(
            start_id=start_id,
            child_id=self.child_id,
            edge_types=edge_types,
            max_depth=max_depth,
            min_confidence=min_confidence,
            limit=limit,
        )
        return Subgraph(nodes=snapshot.nodes, edges=snapshot.edges)

    async def shortest_path(self, source_id: str, target_id: str) -> list[str]:
        return await self._backend.shortest_path(source_id, target_id)

    async def get_neighborhood(self, node_id: str, radius: int = 2) -> Subgraph:
        snapshot = await self._backend.neighborhood(node_id, self.child_id, radius)
        return Subgraph(nodes=snapshot.nodes, edges=snapshot.edges)

    async def find_inference_chain(self, from_type: NodeType, to_type: NodeType) -> list[dict]:
        return await self._backend.find_inference_chains(self.child_id, from_type, to_type)

    async def find_contradictions(self) -> list[tuple[Node, Node, float]]:
        return await self._backend.find_contradictions(self.child_id)

    async def get_nodes_by_type(self, node_type: NodeType) -> list[Node]:
        return await self._backend.get_nodes_by_type(self.child_id, node_type)

    async def get_node(self, node_id: str) -> Node | None:
        return await self._backend.get_node(node_id)

    async def get_all_nodes(self) -> list[Node]:
        return await self._backend.get_all_nodes(self.child_id)

    async def export(
        self,
        start_id: str | None = None,
        max_depth: int = 3,
        min_confidence: float = 0.0,
        limit: int = 200,
    ) -> Subgraph:
        snapshot = await self._backend.export_graph(
            child_id=self.child_id,
            start_id=start_id,
            max_depth=max_depth,
            min_confidence=min_confidence,
            limit=limit,
        )
        return Subgraph(nodes=snapshot.nodes, edges=snapshot.edges)

    async def extract_coaching_subgraph(self) -> Subgraph:
        child_id = await self._get_child_node_id()
        if not child_id:
            return Subgraph(nodes=[], edges=[])
        snapshot = await self._backend.coaching_subgraph(child_id, self.child_id)
        return Subgraph(nodes=snapshot.nodes, edges=snapshot.edges)

    async def extract_context_subgraph(
        self, query_embedding=None, query_text: str | None = None
    ) -> Subgraph:
        candidates: list[tuple[str, float]] = []
        if query_embedding is not None:
            candidates.extend(self._faiss.search(query_embedding, top_k=10))
        if query_text and self._keyword:
            candidates.extend(self._keyword.search(query_text, top_k=10))
        if not candidates:
            return Subgraph(nodes=[], edges=[])
        nodes = []
        seen_candidates = set()
        for node_id, score in sorted(candidates, key=lambda item: item[1], reverse=True):
            if node_id in seen_candidates:
                continue
            seen_candidates.add(node_id)
            seed = await self.get_node(node_id)
            if seed:
                nodes.append(seed)
            subgraph = await self.get_neighborhood(node_id, radius=1)
            nodes.extend(subgraph.nodes)
        seen = set()
        unique_nodes = []
        for n in nodes:
            if n.id not in seen:
                seen.add(n.id)
                unique_nodes.append(n)
        return Subgraph(nodes=unique_nodes, edges=[])

    async def query_by_event_date(
        self,
        start: datetime,
        end: datetime,
        node_type: NodeType | None = None,
    ) -> list[Node]:
        return await self._backend.query_by_event_date(self.child_id, start, end, node_type)

    async def get_timeline(self) -> list[Node]:
        return await self._backend.get_timeline(self.child_id)

    async def get_provenance(self, node_id: str) -> list[dict]:
        return await self._backend.get_provenance(node_id, self.child_id)

    async def mark_stale(self, node_id: str) -> int:
        return await self._backend.mark_stale(node_id)

    async def get_stale_nodes(self) -> list[Node]:
        return await self._backend.get_stale_nodes(self.child_id)

    async def compute_convergence(self, node_id: str) -> float:
        return await self._backend.compute_convergence(node_id)

    async def node_count(self) -> int:
        return await self._backend.node_count(self.child_id)

    async def edge_count(self) -> int:
        return await self._backend.edge_count(self.child_id)

    async def summary(self) -> dict:
        nc = await self.node_count()
        ec = await self.edge_count()
        stale = await self.get_stale_nodes()
        return {
            "child_id": self.child_id,
            "nodes": nc,
            "edges": ec,
            "stale_nodes": len(stale),
            "faiss_vectors": self._faiss.size,
            "bm25_docs": self._keyword.size if self._keyword else 0,
        }

    async def _get_child_node_id(self) -> str | None:
        if self._child_node_id:
            return self._child_node_id
        nodes = await self.get_nodes_by_type(NodeType.CHILD)
        if nodes:
            self._child_node_id = nodes[0].id
        return self._child_node_id

    def delete_local_indexes(self) -> None:
        self._faiss.delete()
        if self._keyword:
            self._keyword.delete()
