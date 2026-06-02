from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from sociomemory.engine.income import IncomeEstimator, _bracket_from_monthly
from sociomemory.graph.memory_graph import MemoryGraph
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.storage.neo4j_backend import Neo4jBackend
from sociomemory.storage.vector import FaissIndex


def make_node(node_type: NodeType, **props) -> Node:
    return Node(child_id="test", type=node_type, properties=props, confidence=0.9)


def make_graph_with_nodes(nodes_by_type: dict) -> MemoryGraph:
    neo4j = MagicMock(spec=Neo4jBackend)
    faiss = MagicMock(spec=FaissIndex)
    graph = MemoryGraph(child_id="test", neo4j=neo4j, faiss=faiss)

    async def get_nodes_by_type(node_type):
        return nodes_by_type.get(node_type, [])

    graph.get_nodes_by_type = get_nodes_by_type
    return graph


def test_bracket_from_monthly():
    assert _bracket_from_monthly(10_000) == "low"
    assert _bracket_from_monthly(40_000) == "lower_middle"
    assert _bracket_from_monthly(75_000) == "middle"
    assert _bracket_from_monthly(150_000) == "upper_middle"
    assert _bracket_from_monthly(300_000) == "high"


@pytest.mark.asyncio
async def test_income_from_rent():
    graph = make_graph_with_nodes({
        NodeType.REAL_ESTATE: [make_node(NodeType.REAL_ESTATE, avg_rent_2bhk=35000)],
    })
    estimator = IncomeEstimator(graph)
    result = await estimator.estimate()
    assert result is not None
    assert result.bracket == "upper_middle"
    assert "location_rent" in result.signals_used
    assert result.confidence > 0.3


@pytest.mark.asyncio
async def test_income_from_school_fee():
    graph = make_graph_with_nodes({
        NodeType.SCHOOL: [make_node(NodeType.SCHOOL, fee_yearly=200000)],
    })
    estimator = IncomeEstimator(graph)
    result = await estimator.estimate()
    assert result is not None
    assert "school_fee" in result.signals_used


@pytest.mark.asyncio
async def test_income_convergence_boost():
    graph = make_graph_with_nodes({
        NodeType.REAL_ESTATE: [make_node(NodeType.REAL_ESTATE, avg_rent_2bhk=35000)],
        NodeType.SCHOOL: [make_node(NodeType.SCHOOL, fee_yearly=200000)],
        NodeType.EMPLOYER: [make_node(NodeType.EMPLOYER, name="infosys", industry="IT")],
    })
    estimator = IncomeEstimator(graph)
    result = await estimator.estimate()
    assert result is not None
    assert result.confidence >= 0.5
    assert len(result.signals_used) >= 2


@pytest.mark.asyncio
async def test_income_no_signals_returns_none():
    graph = make_graph_with_nodes({})
    estimator = IncomeEstimator(graph)
    result = await estimator.estimate()
    assert result is None
