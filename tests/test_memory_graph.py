from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.memory_graph import MemoryGraph, Subgraph
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.storage.graph_backend import GraphBackend
from sociomemory.storage.keyword import BM25Index
from sociomemory.storage.vector import FaissIndex


def make_graph(child_id: str = "test_child") -> MemoryGraph:
    backend = MagicMock(spec=GraphBackend)
    backend.merge_node = AsyncMock(return_value=None)
    backend.merge_edge = AsyncMock(return_value=None)
    backend.merge_subgraph = AsyncMock(return_value=None)
    backend.get_nodes_by_type = AsyncMock(return_value=[])
    backend.node_count = AsyncMock(return_value=0)
    backend.edge_count = AsyncMock(return_value=0)
    backend.get_stale_nodes = AsyncMock(return_value=[])
    faiss = MagicMock(spec=FaissIndex)
    faiss.search = MagicMock(return_value=[])
    faiss.size = 0
    return MemoryGraph(child_id=child_id, backend=backend, faiss=faiss)


def make_graph_with_keyword(child_id: str = "test_child") -> MemoryGraph:
    graph = make_graph(child_id)
    keyword = MagicMock(spec=BM25Index)
    keyword.search = MagicMock(return_value=[])
    keyword.add = MagicMock()
    keyword.save = MagicMock()
    keyword.size = 0
    graph._keyword = keyword
    return graph


def make_node(
    node_type: NodeType = NodeType.NEIGHBORHOOD, confidence: float = 0.9, **props
) -> Node:
    return Node(
        child_id="test_child",
        type=node_type,
        properties=props or {"name": "Koramangala"},
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_add_node_calls_backend():
    graph = make_graph()
    node = await graph.add_node(NodeType.NEIGHBORHOOD, {"name": "Koramangala"}, confidence=0.9)
    assert node.type == NodeType.NEIGHBORHOOD
    assert node.child_id == "test_child"
    graph._backend.merge_node.assert_awaited_once_with(node)


@pytest.mark.asyncio
async def test_add_edge_calls_backend():
    graph = make_graph()
    edge = await graph.add_edge("src_id", "tgt_id", EdgeType.LIVES_IN)
    assert edge.type == EdgeType.LIVES_IN
    graph._backend.merge_edge.assert_awaited_once_with(edge)


@pytest.mark.asyncio
async def test_merge_subgraph_uses_transaction():
    graph = make_graph()
    nodes = [make_node(NodeType.NEIGHBORHOOD, name="HSR")]
    edges = [Edge(source_id="a", target_id="b", type=EdgeType.LOCATED_IN)]
    await graph.merge_subgraph(nodes, edges)
    graph._backend.merge_subgraph.assert_awaited_once_with(nodes, edges)


@pytest.mark.asyncio
async def test_merge_subgraph_indexes_keyword_text():
    graph = make_graph_with_keyword()
    node = make_node(NodeType.NEIGHBORHOOD, name="Koramangala", area_type="urban_affluent")

    await graph.merge_subgraph([node], [])

    graph._keyword.add.assert_called_once()
    indexed_id, indexed_text = graph._keyword.add.call_args.args
    assert indexed_id == node.id
    assert "Koramangala" in indexed_text
    graph._keyword.save.assert_called_once()


@pytest.mark.asyncio
async def test_extract_context_subgraph_uses_keyword_hits():
    graph = make_graph_with_keyword()
    node = make_node(NodeType.PLACE, name="Therapy Center")
    graph._keyword.search = MagicMock(return_value=[(node.id, 3.2)])
    graph.get_node = AsyncMock(return_value=node)
    graph.get_neighborhood = AsyncMock(return_value=Subgraph(nodes=[], edges=[]))

    subgraph = await graph.extract_context_subgraph(query_text="therapy")

    assert subgraph.nodes == [node]
    graph._keyword.search.assert_called_once_with("therapy", top_k=10)


@pytest.mark.asyncio
async def test_get_nodes_by_type_empty():
    graph = make_graph()
    result = await graph.get_nodes_by_type(NodeType.SCHOOL)
    assert result == []
    graph._backend.get_nodes_by_type.assert_awaited_once_with("test_child", NodeType.SCHOOL)


@pytest.mark.asyncio
async def test_node_count():
    graph = make_graph()
    graph._backend.node_count = AsyncMock(return_value=42)
    count = await graph.node_count()
    assert count == 42


@pytest.mark.asyncio
async def test_summary():
    graph = make_graph()
    graph._backend.node_count = AsyncMock(return_value=10)
    graph._backend.edge_count = AsyncMock(return_value=20)
    graph._backend.get_stale_nodes = AsyncMock(return_value=[])
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
