from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sociomemory.graph.nodes import Node, NodeType, DataLevel
from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph import cypher as Q

if TYPE_CHECKING:
    from sociomemory.storage.neo4j_backend import Neo4jBackend
    from sociomemory.storage.vector import FaissIndex
    from sociomemory.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class Subgraph:
    """A subset of the memory graph returned by traversal queries."""

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
    """
    The core graph memory for a single child.
    Backed by Neo4j — the graph on disk IS the graph in queries.
    FAISS provides semantic similarity search over node embeddings.
    """

    def __init__(self, child_id: str, neo4j: "Neo4jBackend", faiss: "FaissIndex"):
        self.child_id = child_id
        self._neo4j = neo4j
        self._faiss = faiss
        self._child_node_id: str | None = None  # cached after first use

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

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
        """
        MERGE node by (node_type, key_properties). Returns the node.
        Also indexes embedding in FAISS if provided.
        """
        node = Node(
            child_id=self.child_id,
            type=node_type,
            properties=properties,
            confidence=confidence,
            sensitivity=sensitivity,
            document_date=document_date or datetime.utcnow(),
            event_date=event_date,
            source_chunk=source_chunk,
        )
        props = node.to_neo4j_props()
        now = datetime.utcnow().isoformat()
        await self._neo4j.run_write(
            Q.MERGE_NODE,
            id=node.id,
            child_id=self.child_id,
            node_type=node_type.value,
            props=props,
            now=now,
        )
        if embedding is not None:
            self._faiss.add(node.id, embedding)
            self._faiss.save()
        return node

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
        ttl: datetime | None = None,
    ) -> Edge:
        """MERGE edge. Updates weight (max strategy) if already exists."""
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            weight=weight,
            properties=properties or {},
            ttl=ttl,
        )
        props = edge.to_neo4j_props()
        cypher = Q.build_merge_edge(edge_type.value)
        await self._neo4j.run_write(
            cypher,
            source_id=source_id,
            target_id=target_id,
            weight=weight,
            props=props,
            now=datetime.utcnow().isoformat(),
        )
        return edge

    async def merge_subgraph(self, nodes: list[Node], edges: list[Edge]) -> None:
        """Atomic transaction: merge all enrichment results at once."""
        queries: list[tuple[str, dict]] = []
        now = datetime.utcnow().isoformat()
        for node in nodes:
            props = node.to_neo4j_props()
            queries.append((
                Q.MERGE_NODE,
                {"id": node.id, "child_id": self.child_id,
                 "node_type": node.type.value, "props": props, "now": now},
            ))
        for edge in edges:
            props = edge.to_neo4j_props()
            queries.append((
                Q.build_merge_edge(edge.type.value),
                {"source_id": edge.source_id, "target_id": edge.target_id,
                 "weight": edge.weight, "props": props, "now": now},
            ))
        await self._neo4j.run_in_transaction(queries)

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    async def traverse(
        self,
        start_id: str,
        edge_types: list[EdgeType] | None = None,
        max_depth: int = 5,
        min_confidence: float = 0.3,
        limit: int = 50,
    ) -> Subgraph:
        """Traverse from a node, optionally filtered by edge types."""
        if edge_types:
            cypher = Q.build_traverse_with_types(
                [e.value for e in edge_types], max_depth
            )
        else:
            cypher = Q.TRAVERSE
        records = await self._neo4j.run(
            cypher,
            start_id=start_id,
            child_id=self.child_id,
            max_depth=max_depth,
            min_confidence=min_confidence,
            limit=limit,
        )
        return self._parse_path_records(records)

    async def shortest_path(self, source_id: str, target_id: str) -> list[str]:
        """Find shortest path between two nodes. Returns list of node IDs."""
        records = await self._neo4j.run(
            Q.SHORTEST_PATH,
            source_id=source_id,
            target_id=target_id,
        )
        if records:
            return records[0].get("node_ids", [])
        return []

    async def get_neighborhood(self, node_id: str, radius: int = 2) -> Subgraph:
        """Get all nodes within N hops."""
        records = await self._neo4j.run(
            Q.NEIGHBORHOOD,
            node_id=node_id,
            child_id=self.child_id,
            radius=radius,
        )
        nodes = [self._parse_node(r["neighbor"]) for r in records if r.get("neighbor")]
        return Subgraph(nodes=nodes, edges=[])

    async def find_inference_chain(
        self, from_type: NodeType, to_type: NodeType
    ) -> list[dict]:
        """Find all paths between two node types."""
        records = await self._neo4j.run(
            Q.FIND_INFERENCE_CHAIN,
            child_id=self.child_id,
            from_type=from_type.value,
            to_type=to_type.value,
        )
        return records

    async def find_contradictions(self) -> list[tuple[Node, Node, float]]:
        """Find all CONTRADICTS edges."""
        records = await self._neo4j.run(
            Q.FIND_CONTRADICTIONS, child_id=self.child_id
        )
        result = []
        for r in records:
            a = self._parse_node(r["a"]) if r.get("a") else None
            b = self._parse_node(r["b"]) if r.get("b") else None
            if a and b:
                result.append((a, b, r.get("tension_score", 0.5)))
        return result

    async def get_nodes_by_type(self, node_type: NodeType) -> list[Node]:
        """Get all nodes of a given type for this child."""
        records = await self._neo4j.run(
            Q.GET_NODES_BY_TYPE,
            child_id=self.child_id,
            node_type=node_type.value,
        )
        return [self._parse_node(r["n"]) for r in records if r.get("n")]

    async def get_node(self, node_id: str) -> Node | None:
        """Fetch a single node by ID."""
        records = await self._neo4j.run(Q.GET_NODE_BY_ID, id=node_id)
        if records and records[0].get("n"):
            return self._parse_node(records[0]["n"])
        return None

    # ------------------------------------------------------------------
    # Subgraph extraction
    # ------------------------------------------------------------------

    async def extract_coaching_subgraph(self) -> Subgraph:
        """Walk from child to all IMPLICATION nodes, including full paths."""
        child_id = await self._get_child_node_id()
        if not child_id:
            return Subgraph(nodes=[], edges=[])
        records = await self._neo4j.run(
            Q.COACHING_SUBGRAPH,
            child_node_id=child_id,
            child_id=self.child_id,
        )
        return self._parse_path_records(records)

    async def extract_context_subgraph(self, query_embedding) -> Subgraph:
        """Semantic search: FAISS top-K → expand neighborhoods via Neo4j."""
        candidates = self._faiss.search(query_embedding, top_k=10)
        if not candidates:
            return Subgraph(nodes=[], edges=[])
        nodes = []
        for node_id, score in candidates:
            subgraph = await self.get_neighborhood(node_id, radius=1)
            nodes.extend(subgraph.nodes)
        # Deduplicate
        seen = set()
        unique_nodes = []
        for n in nodes:
            if n.id not in seen:
                seen.add(n.id)
                unique_nodes.append(n)
        return Subgraph(nodes=unique_nodes, edges=[])

    # ------------------------------------------------------------------
    # Temporal queries
    # ------------------------------------------------------------------

    async def query_by_event_date(
        self,
        start: datetime,
        end: datetime,
        node_type: NodeType | None = None,
    ) -> list[Node]:
        """Find nodes where the event happened in a date range (uses event_date)."""
        cypher = Q.build_event_date_query(
            node_type.value if node_type else None
        )
        records = await self._neo4j.run(
            cypher,
            child_id=self.child_id,
            start=start.isoformat(),
            end=end.isoformat(),
        )
        return [self._parse_node(r["n"]) for r in records if r.get("n")]

    async def get_timeline(self) -> list[Node]:
        """Chronological history sorted by event_date."""
        records = await self._neo4j.run(Q.GET_TIMELINE, child_id=self.child_id)
        return [self._parse_node(r["n"]) for r in records if r.get("n")]

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    async def get_provenance(self, node_id: str) -> list[dict]:
        """
        Trace full DERIVES chain back to source conversation chunks.
        Returns list of {id, node_type, source_chunk, document_date}.
        """
        records = await self._neo4j.run(
            Q.GET_PROVENANCE_CHAIN,
            node_id=node_id,
            child_id=self.child_id,
        )
        if records:
            return records[0].get("provenance_chain", [])
        return []

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    async def mark_stale(self, node_id: str) -> int:
        """Mark node and all DERIVES descendants as stale. Returns count marked."""
        records = await self._neo4j.run_write(
            Q.MARK_STALE_CASCADE, node_id=node_id
        )
        return records[0].get("marked_count", 0) if records else 0

    async def get_stale_nodes(self) -> list[Node]:
        """Return all stale nodes for this child."""
        records = await self._neo4j.run(
            Q.GET_STALE_NODES, child_id=self.child_id
        )
        return [self._parse_node(r["n"]) for r in records if r.get("n")]

    # ------------------------------------------------------------------
    # Confidence / convergence
    # ------------------------------------------------------------------

    async def compute_convergence(self, node_id: str) -> float:
        """How many independent paths lead to this node?"""
        records = await self._neo4j.run(Q.COMPUTE_CONVERGENCE, node_id=node_id)
        if records:
            return float(records[0].get("convergence_count", 0))
        return 0.0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def node_count(self) -> int:
        records = await self._neo4j.run(Q.NODE_COUNT, child_id=self.child_id)
        return records[0].get("count", 0) if records else 0

    async def edge_count(self) -> int:
        records = await self._neo4j.run(Q.EDGE_COUNT, child_id=self.child_id)
        return records[0].get("count", 0) if records else 0

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
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_child_node_id(self) -> str | None:
        """Get or cache the CHILD node ID for this child."""
        if self._child_node_id:
            return self._child_node_id
        nodes = await self.get_nodes_by_type(NodeType.CHILD)
        if nodes:
            self._child_node_id = nodes[0].id
        return self._child_node_id

    def _parse_node(self, record: Any) -> Node:
        """Parse a Neo4j node record into a Node object."""
        if hasattr(record, "_properties"):
            props = dict(record._properties)
        elif isinstance(record, dict):
            props = dict(record)
        else:
            props = {}

        node_type_str = props.pop("node_type", "Signal")
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            node_type = NodeType.SIGNAL

        child_id = props.pop("child_id", self.child_id)
        return Node.from_neo4j(props, node_type=node_type, child_id=child_id)

    def _parse_path_records(self, records: list[dict]) -> Subgraph:
        """Parse path query results into a Subgraph."""
        seen_nodes: dict[str, Node] = {}
        all_edges: list[dict] = []
        for record in records:
            path_nodes = record.get("path_nodes", [])
            path_rels = record.get("path_rels", [])
            for raw_node in path_nodes:
                node = self._parse_node(raw_node)
                if node.id not in seen_nodes:
                    seen_nodes[node.id] = node
            for rel in path_rels:
                if hasattr(rel, "_properties"):
                    all_edges.append(dict(rel._properties))
                elif isinstance(rel, dict):
                    all_edges.append(rel)
        return Subgraph(nodes=list(seen_nodes.values()), edges=all_edges)
