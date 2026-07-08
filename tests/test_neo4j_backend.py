from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from sociomemory.graph import cypher as Q
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.storage.neo4j_backend import Neo4jBackend


def make_backend() -> Neo4jBackend:
    return Neo4jBackend("bolt://localhost:7687", "neo4j", "password")


@pytest.mark.asyncio
async def test_merge_node_translates_domain_node_to_cypher_params():
    backend = make_backend()
    backend.run_write = AsyncMock(return_value=[])
    node = Node(
        id="node-1",
        child_id="child-1",
        type=NodeType.CITY,
        properties={"name": "Bengaluru"},
    )

    await backend.merge_node(node)

    (query,) = backend.run_write.call_args.args
    params = backend.run_write.call_args.kwargs
    assert query == Q.MERGE_NODE
    assert params["id"] == "node-1"
    assert params["node_type"] == "City"
    assert params["props"]["name"] == "Bengaluru"


@pytest.mark.asyncio
async def test_get_nodes_by_type_converts_backend_record_to_domain_node():
    backend = make_backend()
    node = Node(
        id="node-1",
        child_id="child-1",
        type=NodeType.CITY,
        properties={"name": "Bengaluru"},
    )
    backend.run = AsyncMock(return_value=[{"n": node.to_storage_props()}])

    result = await backend.get_nodes_by_type("child-1", NodeType.CITY)

    assert result == [node]


@pytest.mark.asyncio
async def test_export_graph_returns_backend_neutral_snapshot():
    backend = make_backend()
    node = Node(id="node-1", child_id="child-1", type=NodeType.CHILD)
    edge = {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2",
        "type": "LIVES_IN",
        "weight": 1.0,
        "properties": {},
    }
    backend.run = AsyncMock(return_value=[{"nodes": [node.to_storage_props()], "edges": [edge]}])

    snapshot = await backend.export_graph("child-1")

    assert snapshot.nodes == [node]
    assert snapshot.edges == [edge]
