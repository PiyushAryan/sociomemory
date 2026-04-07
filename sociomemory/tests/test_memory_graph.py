"""Tests for MemoryGraph CRUD, traversal, and persistence."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.memory_graph import MemoryGraph, Subgraph
from sociomemory.graph.nodes import DataLevel, Node, NodeType
from sociomemory.storage.neo4j_backend import Neo4jBackend
from sociomemory.storage.vector import FaissIndex


def make_graph(child_id: str = "test_child") -> MemoryGraph:
    neo4j = MagicMock(spec=Neo4jBackend)
    neo4j.run = AsyncMock(return_value=[])
    neo4j.run_write = AsyncMock(return_value=[])
    neo4j.run_in_transaction = AsyncMock(return_value=None)
    faiss = MagicMock(spec=FaissIndex)
    faiss.search = MagicMock(return_value=[])
    faiss.size = 0
    return MemoryGraph(child_id=child_id, neo4j=neo4j, faiss=faiss)


def make_node(node_type: NodeType = NodeType.NEIGHBORHOOD, confidence: float = 0.9, **props) -> Node:
    return Node(
        child_id="test_child",
        type=node_type,
        properties=props or {"name": "Koramangala"},
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_add_node_calls_neo4j():
    graph = make_graph()
    graph._neo4j.run_write = AsyncMock(return_value=[])
    node = await graph.add_node(NodeType.NEIGHBORHOOD, {"name": "Koramangala"}, confidence=0.9)
    assert node.type == NodeType.NEIGHBORHOOD
    assert node.child_id == "test_child"
    graph._neo4j.run_write.assert_called_once()


@pytest.mark.asyncio
async def test_add_edge_calls_neo4j():
    graph = make_graph()
    graph._neo4j.run_write = AsyncMock(return_value=[])
    edge = await graph.add_edge("src_id", "tgt_id", EdgeType.LIVES_IN)
    assert edge.type == EdgeType.LIVES_IN
    graph._neo4j.run_write.assert_called_once()


@pytest.mark.asyncio
async def test_merge_subgraph_uses_transaction():
    graph = make_graph()
    nodes = [make_node(NodeType.NEIGHBORHOOD, name="HSR")]
    edges = [Edge(source_id="a", target_id="b", type=EdgeType.LOCATED_IN)]
    await graph.merge_subgraph(nodes, edges)
    graph._neo4j.run_in_transaction.assert_called_once()


@pytest.mark.asyncio
async def test_get_nodes_by_type_empty():
    graph = make_graph()
    graph._neo4j.run = AsyncMock(return_value=[])
    result = await graph.get_nodes_by_type(NodeType.SCHOOL)
    assert result == []


@pytest.mark.asyncio
async def test_node_count():
    graph = make_graph()
    graph._neo4j.run = AsyncMock(return_value=[{"count": 42}])
    count = await graph.node_count()
    assert count == 42


@pytest.mark.asyncio
async def test_summary():
    graph = make_graph()
    graph._neo4j.run = AsyncMock(side_effect=[
        [{"count": 10}],  # node_count
        [{"count": 20}],  # edge_count
        [],               # get_stale_nodes
    ])
    graph._faiss.size = 5
    result = await graph.summary()
    assert result["nodes"] == 10
    assert result["edges"] == 20
    assert result["faiss_vectors"] == 5


def test_subgraph_aggregate_score():
    nodes = [
        make_node(confidence=0.8),
        make_node(confidence=0.6),
    ]
    sg = Subgraph(nodes=nodes, edges=[])
    assert abs(sg.aggregate_score() - 0.7) < 0.01


def test_subgraph_get_nodes_by_type():
    nodes = [
        make_node(NodeType.NEIGHBORHOOD),
        make_node(NodeType.SCHOOL),
        make_node(NodeType.NEIGHBORHOOD),
    ]
    sg = Subgraph(nodes=nodes, edges=[])
    hoods = sg.get_nodes_by_type(NodeType.NEIGHBORHOOD)
    assert len(hoods) == 2
