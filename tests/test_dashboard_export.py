from __future__ import annotations

import pytest

from sociomemory.dashboard.export import (
    DashboardService,
    config_from_env,
    edge_to_dict,
    node_to_dict,
)
from sociomemory.graph.memory_graph import Subgraph
from sociomemory.graph.nodes import DataLevel, Node, NodeType


def test_config_from_env_defaults_to_openai_when_openai_key_exists(monkeypatch):
    monkeypatch.delenv("SOCIOMEMORY_LLM_BACKEND", raising=False)
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    config = config_from_env()

    assert config.llm_backend == "openai"
    assert config.llm_api_key == "sk-test"


def test_config_from_env_defaults_to_openai_without_backend_env(monkeypatch):
    monkeypatch.delenv("SOCIOMEMORY_LLM_BACKEND", raising=False)
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    config = config_from_env()

    assert config.llm_backend == "openai"
    assert config.llm_api_key == ""


def test_config_from_env_does_not_default_neo4j_credentials(monkeypatch):
    monkeypatch.delenv("SOCIOMEMORY_NEO4J_USER", raising=False)
    monkeypatch.delenv("NEO4J_USER", raising=False)
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("SOCIOMEMORY_NEO4J_PASSWORD", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    config = config_from_env()

    assert config.neo4j_user == ""
    assert config.neo4j_password == ""


def test_config_from_env_reads_neo4j_credentials_from_env(monkeypatch):
    monkeypatch.setenv("SOCIOMEMORY_NEO4J_USER", "configured-user")
    monkeypatch.setenv("SOCIOMEMORY_NEO4J_PASSWORD", "configured-password")

    config = config_from_env()

    assert config.neo4j_user == "configured-user"
    assert config.neo4j_password == "configured-password"


def make_node(node_id: str = "node-1", **props) -> Node:
    return Node(
        id=node_id,
        child_id="child_001",
        type=NodeType.NEIGHBORHOOD,
        properties=props or {"name": "Koramangala"},
        confidence=0.72,
        sensitivity=DataLevel.CONTEXTUAL,
        source_chunk="We live in Koramangala.",
    )


class FakeNeo4j:
    def __init__(self, records):
        self.records = records
        self.calls = []

    async def run(self, query, **params):
        self.calls.append((query, params))
        return self.records


class FakeGraph:
    def __init__(self, records):
        self._neo4j = FakeNeo4j(records)
        self.records = records
        self.node = make_node()

    def _parse_node(self, record):
        if isinstance(record, Node):
            return record
        return make_node(record.get("id", "node-1"), name=record.get("name", "Koramangala"))

    async def summary(self):
        return {
            "child_id": "child_001",
            "nodes": 1,
            "edges": 1,
            "stale_nodes": 0,
            "faiss_vectors": 0,
        }

    async def get_node(self, node_id):
        return self.node if node_id == self.node.id else None

    async def get_provenance(self, node_id):
        return [{"id": "source-1", "source_chunk": "We live in Koramangala."}]

    async def compute_convergence(self, node_id):
        return 2.0

    async def get_stale_nodes(self):
        return []

    async def export(self, **kwargs):
        record = self.records[0] if self.records else {}
        return Subgraph(nodes=record.get("nodes", []), edges=record.get("edges", []))


class FakeMemory:
    def __init__(self, graph):
        self.graph = graph

    async def get_graph(self, child_id):
        return self.graph

    async def segment_episodes(self, child_id):
        return {"child_id": child_id, "episodes": 1, "episode_ids": ["episode-1"]}

    async def acquire_location(self, child_id, lat, lng, accuracy_m=None):
        return {
            "child_id": child_id,
            "location": "Koramangala, Bengaluru",
            "lat": lat,
            "lng": lng,
            "accuracy_m": accuracy_m,
            "enriched": 1,
        }


def test_node_to_dict_keeps_graph_explorer_fields():
    payload = node_to_dict(make_node())
    assert payload["id"] == "node-1"
    assert payload["type"] == "Neighborhood"
    assert payload["label"] == "Koramangala"
    assert payload["confidence"] == 0.72
    assert payload["sensitivity"] == "contextual"
    assert payload["source_chunk"] == "We live in Koramangala."


def test_edge_to_dict_normalizes_neo4j_projection():
    payload = edge_to_dict(
        {
            "id": "edge-1",
            "source": "a",
            "target": "b",
            "type": "LIVES_IN",
            "weight": 0.8,
            "properties": {"created_at": "today"},
        }
    )
    assert payload == {
        "id": "edge-1",
        "source": "a",
        "target": "b",
        "type": "LIVES_IN",
        "weight": 0.8,
        "properties": {"created_at": "today"},
    }


def test_dashboard_export_queries_avoid_direct_relationship_weight_reads():
    from sociomemory.dashboard import export

    assert ".weight" not in export.ALL_GRAPH_QUERY
    assert ".weight" not in export.build_traverse_export_query()


@pytest.mark.asyncio
async def test_graph_export_returns_nodes_and_edges_without_neo4j_service():
    node = make_node()
    records = [
        {
            "nodes": [node],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "child-node",
                    "target": node.id,
                    "type": "LIVES_IN",
                    "weight": 1.0,
                    "properties": {},
                }
            ],
        }
    ]
    service = DashboardService(memory=FakeMemory(FakeGraph(records)))

    payload = await service.graph_export("child_001")

    assert payload["child_id"] == "child_001"
    assert payload["mode"] == "all"
    assert payload["nodes"][0]["id"] == node.id
    assert payload["edges"][0]["type"] == "LIVES_IN"


@pytest.mark.asyncio
async def test_node_detail_includes_provenance_neighbors_and_convergence():
    node = make_node()
    records = [{"nodes": [node], "edges": []}]
    service = DashboardService(memory=FakeMemory(FakeGraph(records)))

    payload = await service.node_detail("child_001", node.id)

    assert payload["node"]["id"] == node.id
    assert payload["provenance"][0]["source_chunk"] == "We live in Koramangala."
    assert payload["neighbors"]["mode"] == "traverse"
    assert payload["convergence"] == 2.0


@pytest.mark.asyncio
async def test_segment_episodes_delegates_to_memory_api():
    service = DashboardService(memory=FakeMemory(FakeGraph([])))

    payload = await service.segment_episodes("child_001")

    assert payload["result"]["episodes"] == 1
    assert payload["result"]["episode_ids"] == ["episode-1"]


@pytest.mark.asyncio
async def test_acquire_location_delegates_to_memory_api():
    service = DashboardService(memory=FakeMemory(FakeGraph([])))

    payload = await service.acquire_location("child_001", 12.935, 77.624, 100.0)

    assert payload["result"]["location"] == "Koramangala, Bengaluru"
    assert payload["result"]["lat"] == 12.935
    assert payload["result"]["accuracy_m"] == 100.0
