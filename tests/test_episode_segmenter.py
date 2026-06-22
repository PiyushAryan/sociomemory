from __future__ import annotations

from datetime import datetime

import pytest

from sociomemory.engine.episodes import EpisodeSegmenter
from sociomemory.graph.edges import EdgeType
from sociomemory.graph.nodes import DataLevel, Node, NodeType


class FakeGraph:
    child_id = "child_001"

    def __init__(self, timeline: list[Node]) -> None:
        self.timeline = timeline
        self.merged_nodes = []
        self.merged_edges = []

    async def get_timeline(self):
        return self.timeline

    async def merge_subgraph(self, nodes, edges):
        self.merged_nodes = nodes
        self.merged_edges = edges


def event(
    node_id: str,
    date: str,
    *,
    node_type: NodeType = NodeType.VISIT,
    confidence: float = 0.8,
    sensitivity: DataLevel = DataLevel.CONTEXTUAL,
    **properties,
) -> Node:
    return Node(
        id=node_id,
        child_id="child_001",
        type=node_type,
        properties=properties or {"place_type": "park"},
        confidence=confidence,
        sensitivity=sensitivity,
        event_date=datetime.fromisoformat(date),
    )


def test_episode_schema_primitives_exist():
    assert NodeType.EPISODE.value == "Episode"
    assert EdgeType.PART_OF.value == "PART_OF"
    assert EdgeType.FOLLOWS.value == "FOLLOWS"


@pytest.mark.asyncio
async def test_segmenter_groups_nearby_events_into_episode():
    graph = FakeGraph(
        [
            event("visit-1", "2026-01-01T10:00:00", place_type="temple", confidence=0.7),
            event("visit-2", "2026-01-05T10:00:00", place_type="temple", confidence=0.9),
            event(
                "signal-1", "2026-01-07T10:00:00", node_type=NodeType.SIGNAL, signal_type="outing"
            ),
        ]
    )

    report = await EpisodeSegmenter(graph).segment()

    assert report["events_considered"] == 3
    assert report["episodes"] == 1
    episode = graph.merged_nodes[0]
    assert episode.type == NodeType.EPISODE
    assert episode.properties["event_count"] == 3
    assert episode.properties["start_date"] == "2026-01-01"
    assert episode.properties["end_date"] == "2026-01-07"
    assert episode.properties["theme"] == "temple"
    assert [edge.type for edge in graph.merged_edges] == [
        EdgeType.PART_OF,
        EdgeType.PART_OF,
        EdgeType.PART_OF,
    ]


@pytest.mark.asyncio
async def test_segmenter_splits_far_apart_events_and_links_episodes():
    graph = FakeGraph(
        [
            event("visit-1", "2026-01-01T10:00:00", place_type="park"),
            event("visit-2", "2026-01-10T10:00:00", place_type="park"),
            event(
                "visit-3", "2026-03-01T10:00:00", place_type="mall", sensitivity=DataLevel.PERSONAL
            ),
        ]
    )

    report = await EpisodeSegmenter(graph).segment()

    assert report["episodes"] == 2
    assert [node.properties["event_count"] for node in graph.merged_nodes] == [2, 1]
    assert graph.merged_nodes[1].sensitivity == DataLevel.PERSONAL
    assert [edge.type for edge in graph.merged_edges].count(EdgeType.PART_OF) == 3
    follows = [edge for edge in graph.merged_edges if edge.type == EdgeType.FOLLOWS]
    assert len(follows) == 1
    assert follows[0].properties["gap_days"] == 50


@pytest.mark.asyncio
async def test_segmenter_uses_stable_episode_ids_from_first_member():
    timeline = [
        event("visit-1", "2026-01-01T10:00:00"),
        event("visit-2", "2026-01-02T10:00:00"),
    ]
    first = FakeGraph(timeline)
    second = FakeGraph(timeline)

    await EpisodeSegmenter(first).segment()
    await EpisodeSegmenter(second).segment()

    assert first.merged_nodes[0].id == second.merged_nodes[0].id
