from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sociomemory.engine.behavioral import BehavioralInference, _confidence
from sociomemory.graph.memory_graph import MemoryGraph
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.storage.graph_backend import GraphBackend
from sociomemory.storage.vector import FaissIndex


def make_visit(place_type: str, place_subtype: str = "") -> Node:
    return Node(
        child_id="test",
        type=NodeType.VISIT,
        properties={"place_type": place_type, "place_subtype": place_subtype},
        confidence=0.8,
    )


def make_graph(visits: list) -> MemoryGraph:
    backend = MagicMock(spec=GraphBackend)
    faiss = MagicMock(spec=FaissIndex)
    graph = MemoryGraph(child_id="test", backend=backend, faiss=faiss)

    async def get_nodes_by_type(node_type):
        if node_type == NodeType.VISIT:
            return visits
        return []

    graph.get_nodes_by_type = get_nodes_by_type
    return graph


def test_confidence_grows_logarithmically():
    c1 = _confidence(1)
    c3 = _confidence(3)
    c5 = _confidence(5)
    assert c1 < c3 < c5
    assert c5 <= 0.95


@pytest.mark.asyncio
async def test_iskcon_visit_infers_krishna_devotee():
    visits = [make_visit("temple", "iskcon")] * 2
    graph = make_graph(visits)
    bi = BehavioralInference(graph)
    identity = await bi.infer_identity()
    assert identity.get("religious", {}).get("identity") == "krishna_devotee"
    assert identity.get("dietary", {}).get("tag") == "vegetarian_likely"


@pytest.mark.asyncio
async def test_mountain_visits_infer_outdoor_active():
    visits = [make_visit("mountain")] * 3
    graph = make_graph(visits)
    bi = BehavioralInference(graph)
    identity = await bi.infer_identity()
    assert "outdoor_active" in identity.get("lifestyle", {})
    assert "cold_tolerant" in identity.get("sensory", {})


@pytest.mark.asyncio
async def test_mosque_visit_infers_muslim_halal():
    visits = [make_visit("mosque")] * 2
    graph = make_graph(visits)
    bi = BehavioralInference(graph)
    identity = await bi.infer_identity()
    assert identity.get("religious", {}).get("identity") == "muslim"
    assert identity.get("dietary", {}).get("tag") == "halal_likely"


@pytest.mark.asyncio
async def test_therapy_opportunities_adventure():
    visits = [make_visit("mountain")] * 3
    graph = make_graph(visits)
    bi = BehavioralInference(graph)
    opps = await bi.suggest_therapy_opportunities()
    opp_types = [o["type"] for o in opps]
    assert "adventure_therapy" in opp_types


@pytest.mark.asyncio
async def test_empty_visits_returns_empty_identity():
    graph = make_graph([])
    bi = BehavioralInference(graph)
    identity = await bi.infer_identity()
    assert identity == {}
