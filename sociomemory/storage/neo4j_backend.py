from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from sociomemory.graph import cypher as Q
from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.storage.graph_backend import GraphSnapshot
from sociomemory.time import utc_now

logger = logging.getLogger(__name__)


class Neo4jBackend:
    SCHEMA_QUERIES = [
        "CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:SocioNode) REQUIRE n.id IS UNIQUE",
        "CREATE INDEX node_child_id IF NOT EXISTS FOR (n:SocioNode) ON (n.child_id)",
        "CREATE INDEX node_event_date IF NOT EXISTS FOR (n:SocioNode) ON (n.event_date)",
        "CREATE INDEX node_stale IF NOT EXISTS FOR (n:SocioNode) ON (n.stale)",
        "CREATE INDEX node_child_date IF NOT EXISTS FOR (n:SocioNode) ON (n.child_id, n.event_date)",
    ]

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database  # AuraDB always uses "neo4j"
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
            max_connection_pool_size=50,
        )
        await self._driver.verify_connectivity()
        logger.info("Neo4j connected: %s (db=%s)", self._uri, self._database)

    def _is_aura(self) -> bool:
        return "databases.neo4j.io" in self._uri or self._uri.startswith("neo4j+s://")

    async def init_schema(self) -> None:
        for q in self.SCHEMA_QUERIES:
            try:
                await self.run_write(q)
            except Exception as exc:
                logger.debug("Schema query skipped (%s): %s", exc, q[:60])

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j not connected. Call connect() first.")
        return self._driver

    async def run(self, query: str, **params: Any) -> list[dict]:
        async with self.driver.session(database=self._database) as session:
            result = await session.run(query, **params)
            return [dict(record) async for record in result]

    async def run_write(self, query: str, **params: Any) -> list[dict]:
        async with self.driver.session(database=self._database) as session:
            result = await session.run(query, **params)
            return [dict(record) async for record in result]

    async def run_in_transaction(self, queries: list[tuple[str, dict]]) -> None:
        async with self.driver.session(database=self._database) as session:
            async with await session.begin_transaction() as tx:
                for query, params in queries:
                    await tx.run(query, **params)
                await tx.commit()

    async def health_check(self) -> bool:
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def merge_node(self, node: Node) -> None:
        await self.run_write(
            Q.MERGE_NODE,
            id=node.id,
            child_id=node.child_id,
            node_type=node.type.value,
            props=node.to_storage_props(),
            now=utc_now().isoformat(),
        )

    async def update_node_properties(
        self,
        node_id: str,
        child_id: str,
        node_type: NodeType,
        properties: dict[str, Any],
    ) -> None:
        await self.run_write(
            Q.MERGE_NODE,
            id=node_id,
            child_id=child_id,
            node_type=node_type.value,
            props=properties,
            now=utc_now().isoformat(),
        )

    async def merge_edge(self, edge: Edge) -> None:
        await self.run_write(
            Q.build_merge_edge(edge.type.value),
            source_id=edge.source_id,
            target_id=edge.target_id,
            weight=edge.weight,
            props=edge.to_storage_props(),
            now=utc_now().isoformat(),
        )

    async def merge_subgraph(self, nodes: list[Node], edges: list[Edge]) -> None:
        now = utc_now().isoformat()
        queries: list[tuple[str, dict]] = []
        for node in nodes:
            queries.append(
                (
                    Q.MERGE_NODE,
                    {
                        "id": node.id,
                        "child_id": node.child_id,
                        "node_type": node.type.value,
                        "props": node.to_storage_props(),
                        "now": now,
                    },
                )
            )
        for edge in edges:
            queries.append(
                (
                    Q.build_merge_edge(edge.type.value),
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "weight": edge.weight,
                        "props": edge.to_storage_props(),
                        "now": now,
                    },
                )
            )
        await self.run_in_transaction(queries)

    async def traverse(
        self,
        start_id: str,
        child_id: str,
        edge_types: list[EdgeType] | None,
        max_depth: int,
        min_confidence: float,
        limit: int,
    ) -> GraphSnapshot:
        query = (
            Q.build_traverse_with_types([edge.value for edge in edge_types], max_depth)
            if edge_types
            else Q.build_traverse(max_depth)
        )
        records = await self.run(
            query,
            start_id=start_id,
            child_id=child_id,
            min_confidence=min_confidence,
            limit=limit,
        )
        return self._parse_path_records(records)

    async def shortest_path(self, source_id: str, target_id: str) -> list[str]:
        records = await self.run(
            Q.SHORTEST_PATH,
            source_id=source_id,
            target_id=target_id,
        )
        return records[0].get("node_ids", []) if records else []

    async def neighborhood(self, node_id: str, child_id: str, radius: int) -> GraphSnapshot:
        records = await self.run(
            Q.build_neighborhood(radius),
            node_id=node_id,
            child_id=child_id,
        )
        nodes = [
            self._parse_node(record["neighbor"]) for record in records if record.get("neighbor")
        ]
        return GraphSnapshot(nodes=nodes)

    async def find_inference_chains(
        self, child_id: str, from_type: NodeType, to_type: NodeType
    ) -> list[dict[str, Any]]:
        records = await self.run(
            Q.FIND_INFERENCE_CHAIN,
            child_id=child_id,
            from_type=from_type.value,
            to_type=to_type.value,
        )
        result = []
        for record in records:
            result.append(
                {
                    **record,
                    "path_nodes": [self._parse_node(node) for node in record.get("path_nodes", [])],
                    "path_rels": [self._edge_to_dict(edge) for edge in record.get("path_rels", [])],
                }
            )
        return result

    async def find_contradictions(self, child_id: str) -> list[tuple[Node, Node, float]]:
        records = await self.run(Q.FIND_CONTRADICTIONS, child_id=child_id)
        return [
            (
                self._parse_node(record["a"]),
                self._parse_node(record["b"]),
                float(record.get("tension_score", 0.5)),
            )
            for record in records
            if record.get("a") and record.get("b")
        ]

    async def get_nodes_by_type(self, child_id: str, node_type: NodeType) -> list[Node]:
        records = await self.run(
            Q.GET_NODES_BY_TYPE,
            child_id=child_id,
            node_type=node_type.value,
        )
        return [self._parse_node(record["n"]) for record in records if record.get("n")]

    async def get_node(self, node_id: str) -> Node | None:
        records = await self.run(Q.GET_NODE_BY_ID, id=node_id)
        return self._parse_node(records[0]["n"]) if records and records[0].get("n") else None

    async def get_all_nodes(self, child_id: str) -> list[Node]:
        records = await self.run(Q.GET_ALL_NODES, child_id=child_id)
        return [self._parse_node(record["n"]) for record in records if record.get("n")]

    async def coaching_subgraph(self, child_node_id: str, child_id: str) -> GraphSnapshot:
        records = await self.run(
            Q.COACHING_SUBGRAPH,
            child_node_id=child_node_id,
            child_id=child_id,
        )
        return self._parse_path_records(records)

    async def query_by_event_date(
        self,
        child_id: str,
        start: datetime,
        end: datetime,
        node_type: NodeType | None,
    ) -> list[Node]:
        records = await self.run(
            Q.build_event_date_query(node_type.value if node_type else None),
            child_id=child_id,
            start=start.isoformat(),
            end=end.isoformat(),
            node_type=node_type.value if node_type else None,
        )
        return [self._parse_node(record["n"]) for record in records if record.get("n")]

    async def get_timeline(self, child_id: str) -> list[Node]:
        records = await self.run(Q.GET_TIMELINE, child_id=child_id)
        return [self._parse_node(record["n"]) for record in records if record.get("n")]

    async def get_provenance(self, node_id: str, child_id: str) -> list[dict[str, Any]]:
        records = await self.run(
            Q.GET_PROVENANCE_CHAIN,
            node_id=node_id,
            child_id=child_id,
        )
        return records[0].get("provenance_chain", []) if records else []

    async def mark_stale(self, node_id: str) -> int:
        records = await self.run_write(Q.MARK_STALE_CASCADE, node_id=node_id)
        return int(records[0].get("marked_count", 0)) if records else 0

    async def get_stale_nodes(self, child_id: str) -> list[Node]:
        records = await self.run(Q.GET_STALE_NODES, child_id=child_id)
        return [self._parse_node(record["n"]) for record in records if record.get("n")]

    async def compute_convergence(self, node_id: str) -> float:
        records = await self.run(Q.COMPUTE_CONVERGENCE, node_id=node_id)
        return float(records[0].get("convergence_count", 0)) if records else 0.0

    async def node_count(self, child_id: str) -> int:
        records = await self.run(Q.NODE_COUNT, child_id=child_id)
        return int(records[0].get("count", 0)) if records else 0

    async def edge_count(self, child_id: str) -> int:
        records = await self.run(Q.EDGE_COUNT, child_id=child_id)
        return int(records[0].get("count", 0)) if records else 0

    async def erase_child(self, child_id: str) -> None:
        await self.run_write(Q.ERASE_CHILD, child_id=child_id)

    async def list_children(self, limit: int = 100) -> list[str]:
        records = await self.run(Q.LIST_CHILDREN, limit=limit)
        return [record["child_id"] for record in records if record.get("child_id")]

    async def export_graph(
        self,
        child_id: str,
        start_id: str | None = None,
        max_depth: int = 3,
        min_confidence: float = 0.0,
        limit: int = 200,
    ) -> GraphSnapshot:
        if start_id:
            records = await self.run(
                Q.build_traverse_export(max_depth),
                child_id=child_id,
                start_id=start_id,
                min_confidence=min_confidence,
                limit=limit,
            )
            return self._parse_path_records(records, node_key="nodes", edge_key="edges")

        records = await self.run(Q.EXPORT_GRAPH, child_id=child_id)
        if not records:
            return GraphSnapshot()
        return GraphSnapshot(
            nodes=[self._parse_node(node) for node in records[0].get("nodes", [])],
            edges=[self._edge_to_dict(edge) for edge in records[0].get("edges", [])],
        )

    @staticmethod
    def _parse_node(record: Any) -> Node:
        if hasattr(record, "_properties"):
            props = dict(record._properties)
        elif isinstance(record, dict):
            props = dict(record)
        else:
            props = {}

        node_type_value = props.pop("node_type", NodeType.SIGNAL.value)
        try:
            node_type = NodeType(node_type_value)
        except ValueError:
            node_type = NodeType.SIGNAL
        child_id = props.pop("child_id", "")
        return Node.from_storage(props, node_type=node_type, child_id=child_id)

    @staticmethod
    def _edge_to_dict(record: Any) -> dict[str, Any]:
        if isinstance(record, dict):
            return dict(record)
        properties = dict(getattr(record, "_properties", {}) or {})
        return properties

    def _parse_path_records(
        self,
        records: list[dict],
        node_key: str = "path_nodes",
        edge_key: str = "path_rels",
    ) -> GraphSnapshot:
        nodes: dict[str, Node] = {}
        edges: list[dict[str, Any]] = []
        for record in records:
            for raw_node in record.get(node_key, []):
                node = self._parse_node(raw_node)
                nodes[node.id] = node
            edges.extend(self._edge_to_dict(edge) for edge in record.get(edge_key, []))
        return GraphSnapshot(nodes=list(nodes.values()), edges=edges)
