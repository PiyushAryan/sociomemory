from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sociomemory import Sociomemory, SociomemoryConfig
from sociomemory.graph.nodes import Node

ALL_GRAPH_QUERY = """
MATCH (n:SocioNode {child_id: $child_id})
OPTIONAL MATCH (n)-[r]->(m:SocioNode {child_id: $child_id})
WITH collect(DISTINCT n) AS nodes,
     collect(DISTINCT CASE
       WHEN r IS NULL THEN null
       ELSE {
         id: r.id,
         type: type(r),
         source: n.id,
         target: m.id,
         weight: coalesce(properties(r)['weight'], 1.0),
         properties: properties(r)
       }
     END) AS edges
RETURN nodes, [edge IN edges WHERE edge IS NOT NULL] AS edges
"""


# Neo4j forbids parameters in the variable-length bound (`*1..$n`); inline an
# int-coerced depth instead (coercion also prevents injection).
def build_traverse_export_query(max_depth: int = 3) -> str:
    depth = int(max_depth)
    return f"""
MATCH path = (start:SocioNode {{id: $start_id}})-[r*1..{depth}]->(end:SocioNode)
WHERE start.child_id = $child_id
  AND end.child_id = $child_id
  AND ALL(rel IN relationships(path) WHERE coalesce(properties(rel)['weight'], 1.0) >= $min_confidence)
WITH nodes(path) AS path_nodes,
     [rel IN relationships(path) | {{
       id: rel.id,
       type: type(rel),
       source: startNode(rel).id,
       target: endNode(rel).id,
       weight: coalesce(properties(rel)['weight'], 1.0),
       properties: properties(rel)
     }}] AS path_rels
RETURN path_nodes AS nodes, path_rels AS edges
LIMIT $limit
"""


CHILDREN_QUERY = """
MATCH (n:SocioNode)
WHERE n.child_id IS NOT NULL
RETURN DISTINCT n.child_id AS child_id
ORDER BY child_id
LIMIT $limit
"""


@dataclass
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8765


def config_from_env() -> SociomemoryConfig:
    data_dir = os.getenv("SOCIOMEMORY_DATA_DIR")
    backend = os.getenv("SOCIOMEMORY_LLM_BACKEND") or os.getenv("LLM_BACKEND") or _default_llm_backend()
    # Backend-aware key: prefer provider-specific keys so stale generic keys
    # don't shadow the intended provider.
    backend_key = {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
        "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
    }.get(backend.lower(), "")
    llm_api_key = (
        backend_key
        or os.getenv("LLM_API_KEY", "")
        or os.getenv("OPENROUTER_API_KEY", "")
    )
    return SociomemoryConfig(
        neo4j_uri=os.getenv(
            "SOCIOMEMORY_NEO4J_URI", os.getenv("NEO4J_URI", "bolt://localhost:7687")
        ),
        neo4j_user=_env_first("SOCIOMEMORY_NEO4J_USER", "NEO4J_USER", "NEO4J_USERNAME"),
        neo4j_password=_env_first("SOCIOMEMORY_NEO4J_PASSWORD", "NEO4J_PASSWORD"),
        neo4j_database=os.getenv(
            "SOCIOMEMORY_NEO4J_DATABASE", os.getenv("NEO4J_DATABASE", "neo4j")
        ),
        llm_backend=backend,
        llm_api_key=llm_api_key,
        llm_model=os.getenv(
            "SOCIOMEMORY_LLM_MODEL",
            os.getenv("LLM_MODEL", os.getenv("OPENROUTER_MODEL", "")),
        ),
        llm_embedding_model=os.getenv(
            "SOCIOMEMORY_LLM_EMBEDDING_MODEL",
            os.getenv("LLM_EMBEDDING_MODEL", os.getenv("OPENROUTER_EMBEDDING_MODEL", "")),
        ),
        data_dir=Path(data_dir).expanduser() if data_dir else Path.home() / ".sociomemory",
        offline_only=os.getenv("SOCIOMEMORY_OFFLINE_ONLY", "").lower() in {"1", "true", "yes"},
        country=os.getenv("SOCIOMEMORY_COUNTRY", "IN"),
        embedding_dim=int(os.getenv("SOCIOMEMORY_EMBEDDING_DIM", "768")),
        exa_api_key=os.getenv("SOCIOMEMORY_EXA_API_KEY", os.getenv("EXA_API_KEY", "")),
    )


def _env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return ""


def _default_llm_backend() -> str:
    return "openai"


def node_to_dict(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "child_id": node.child_id,
        "type": node.type.value,
        "properties": node.properties,
        "confidence": node.confidence,
        "sensitivity": node.sensitivity.value,
        "document_date": node.document_date.isoformat() if node.document_date else None,
        "event_date": node.event_date.isoformat() if node.event_date else None,
        "source_chunk": node.source_chunk,
        "stale": node.stale,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        "label": node.properties.get("name")
        or node.properties.get("title")
        or node.properties.get("value")
        or node.type.value,
    }


def edge_to_dict(edge: dict[str, Any]) -> dict[str, Any]:
    props = dict(edge.get("properties") or {})
    edge_id = edge.get("id") or props.get("id")
    weight = edge.get("weight", props.get("weight", 1.0))
    return {
        "id": edge_id,
        "source": edge.get("source") or edge.get("source_id"),
        "target": edge.get("target") or edge.get("target_id"),
        "type": edge.get("type") or edge.get("edge_type") or props.get("type") or "RELATED",
        "weight": float(weight or 1.0),
        "properties": props,
    }


class DashboardService:
    def __init__(
        self,
        config: SociomemoryConfig | None = None,
        memory: Sociomemory | Any | None = None,
    ) -> None:
        self._config = (
            config if config is not None else (config_from_env() if memory is None else None)
        )
        self._memory = memory
        self._owns_memory = memory is None

    @classmethod
    def from_env(cls) -> DashboardService:
        return cls(config=config_from_env())

    async def connect(self) -> None:
        if self._memory is None:
            if self._config is None:
                self._config = config_from_env()
            self._memory = Sociomemory(self._config)
            await self._memory.connect()

    async def close(self) -> None:
        if self._owns_memory and self._memory is not None:
            await self._memory.close()

    async def list_children(self, limit: int = 100) -> dict[str, Any]:
        return {"children": await self._memory.list_children(limit=limit)}

    async def summary(self, child_id: str) -> dict[str, Any]:
        graph = await self._memory.get_graph(child_id)
        summary = await graph.summary()
        return {"summary": summary}

    async def graph_export(
        self,
        child_id: str,
        start_id: str | None = None,
        max_depth: int = 3,
        min_confidence: float = 0.0,
        limit: int = 200,
    ) -> dict[str, Any]:
        graph = await self._memory.get_graph(child_id)
        subgraph = await graph.export(
            start_id=start_id,
            max_depth=max_depth,
            min_confidence=min_confidence,
            limit=limit,
        )
        return {
            "child_id": child_id,
            "nodes": [node_to_dict(node) for node in subgraph.nodes],
            "edges": _dedupe_edges(edge_to_dict(edge) for edge in subgraph.edges),
            "mode": "traverse" if start_id else "all",
        }

    async def node_detail(self, child_id: str, node_id: str) -> dict[str, Any]:
        graph = await self._memory.get_graph(child_id)
        node = await graph.get_node(node_id)
        if node is None:
            raise LookupError(f"Node not found: {node_id}")
        provenance = await graph.get_provenance(node_id)
        neighbors = await self.graph_export(child_id, start_id=node_id, max_depth=1, limit=50)
        convergence = await graph.compute_convergence(node_id)
        return {
            "node": node_to_dict(node),
            "provenance": provenance,
            "neighbors": neighbors,
            "convergence": convergence,
        }

    async def stale_nodes(self, child_id: str) -> dict[str, Any]:
        graph = await self._memory.get_graph(child_id)
        nodes = await graph.get_stale_nodes()
        return {"nodes": [node_to_dict(node) for node in nodes]}

    async def profile(self, child_id: str) -> dict[str, Any]:
        profile = await self._memory.get_profile(child_id)
        return {"profile": profile.model_dump(mode="json")}

    async def context(self, child_id: str) -> dict[str, Any]:
        return {"context": await self._memory.get_context_for_llm(child_id)}

    async def coaching(self, child_id: str) -> dict[str, Any]:
        implications = await self._memory.get_coaching_implications(child_id)
        return {"implications": [item.model_dump(mode="json") for item in implications]}

    async def ingest(
        self, child_id: str, text: str, source: str = "conversation"
    ) -> dict[str, Any]:
        if not text.strip():
            raise ValueError("text is required")
        return {"result": await self._memory.ingest(child_id, text, source=source)}

    async def segment_episodes(self, child_id: str) -> dict[str, Any]:
        return {"result": await self._memory.segment_episodes(child_id)}

    async def ingest_person(
        self,
        child_id: str,
        name: str | None = None,
        area: str | None = None,
        school: str | None = None,
        places: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return {
            "result": await self._memory.ingest_person(
                child_id,
                name=name,
                area=area,
                school=school,
                places=places,
                notes=notes,
            )
        }

    async def acquire_location(
        self,
        child_id: str,
        lat: float,
        lng: float,
        accuracy_m: float | None = None,
    ) -> dict[str, Any]:
        return {"result": await self._memory.acquire_location(child_id, lat, lng, accuracy_m)}

    async def privacy_export(self, child_id: str) -> dict[str, Any]:
        return {"export": self._memory.privacy.export(child_id)}

    async def privacy_erase(self, child_id: str) -> dict[str, Any]:
        await self._memory.privacy.erase(child_id)
        return {"status": "erased", "child_id": child_id}


def _dedupe_edges(edges: Any) -> list[dict[str, Any]]:
    seen: set[tuple[Any, Any, Any, Any]] = set()
    result: list[dict[str, Any]] = []
    for edge in edges:
        key = (edge.get("id"), edge.get("source"), edge.get("target"), edge.get("type"))
        if key in seen:
            continue
        seen.add(key)
        result.append(edge)
    return result
