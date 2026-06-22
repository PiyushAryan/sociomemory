from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import TYPE_CHECKING

from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.nodes import DataLevel, Node, NodeType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph


DEFAULT_EPISODE_TYPES = frozenset(
    {
        NodeType.VISIT,
        NodeType.SENSORY_EVIDENCE,
        NodeType.SIGNAL,
        NodeType.THERAPY_OPPORTUNITY,
    }
)

SENSITIVITY_RANK = {
    DataLevel.PUBLIC: 0,
    DataLevel.CONTEXTUAL: 1,
    DataLevel.PERSONAL: 2,
    DataLevel.SENSITIVE: 3,
}


@dataclass(frozen=True)
class EpisodeSegment:
    episode: Node
    members: list[Node]


class EpisodeSegmenter:
    def __init__(
        self,
        graph: MemoryGraph,
        *,
        default_gap_days: int = 21,
        eligible_types: Iterable[NodeType] | None = None,
    ) -> None:
        self._graph = graph
        self._default_gap_days = default_gap_days
        self._eligible_types = set(eligible_types or DEFAULT_EPISODE_TYPES)

    async def segment(self) -> dict:
        timeline = await self._graph.get_timeline()
        events = self._eligible_events(timeline)
        if not events:
            return {
                "child_id": self._graph.child_id,
                "events_considered": 0,
                "episodes": 0,
                "episode_ids": [],
                "gap_threshold_days": self._default_gap_days,
            }

        gap_threshold = self._adaptive_gap_days(events)
        groups = self._group_events(events, gap_threshold)
        segments = [self._build_segment(group, gap_threshold) for group in groups]

        episode_nodes = [segment.episode for segment in segments]
        edges = self._build_edges(segments)
        await self._graph.merge_subgraph(episode_nodes, edges)

        return {
            "child_id": self._graph.child_id,
            "events_considered": len(events),
            "episodes": len(segments),
            "episode_ids": [segment.episode.id for segment in segments],
            "gap_threshold_days": gap_threshold,
        }

    def _eligible_events(self, nodes: list[Node]) -> list[Node]:
        events = [
            node
            for node in nodes
            if node.event_date is not None and node.type in self._eligible_types
        ]
        return sorted(events, key=lambda node: (node.event_date or datetime.min, node.id))

    def _adaptive_gap_days(self, events: list[Node]) -> int:
        if len(events) < 2:
            return self._default_gap_days
        gaps = []
        for left, right in zip(events, events[1:]):
            if left.event_date and right.event_date:
                gaps.append(max(0, (right.event_date.date() - left.event_date.date()).days))
        if not gaps:
            return self._default_gap_days
        sorted_gaps = sorted(gaps)
        lower_count = max(1, len(sorted_gaps) // 2)
        typical_gap = median(sorted_gaps[:lower_count])
        return max(self._default_gap_days, round(typical_gap * 2.5))

    def _group_events(self, events: list[Node], gap_threshold_days: int) -> list[list[Node]]:
        groups: list[list[Node]] = []
        current: list[Node] = []
        previous: Node | None = None
        for event in events:
            if previous and previous.event_date and event.event_date:
                gap_days = (event.event_date.date() - previous.event_date.date()).days
                if gap_days > gap_threshold_days:
                    groups.append(current)
                    current = []
            current.append(event)
            previous = event
        if current:
            groups.append(current)
        return groups

    def _build_segment(self, members: list[Node], gap_threshold_days: int) -> EpisodeSegment:
        start = min(member.event_date for member in members if member.event_date)
        end = max(member.event_date for member in members if member.event_date)
        confidence = round(sum(member.confidence for member in members) / len(members), 3)
        theme = self._theme(members)
        properties = {
            "name": self._episode_name(theme, start, end),
            "theme": theme,
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
            "span_days": (end.date() - start.date()).days + 1,
            "event_count": len(members),
            "member_ids": [member.id for member in members],
            "member_types": sorted({member.type.value for member in members}),
            "gap_threshold_days": gap_threshold_days,
            "salience": self._salience(confidence, len(members)),
        }
        episode = Node(
            id=self._episode_id(members[0]),
            child_id=self._graph.child_id,
            type=NodeType.EPISODE,
            properties=properties,
            confidence=confidence,
            sensitivity=self._max_sensitivity(members),
            event_date=start,
            stale=any(member.stale for member in members),
        )
        return EpisodeSegment(episode=episode, members=members)

    def _build_edges(self, segments: list[EpisodeSegment]) -> list[Edge]:
        edges: list[Edge] = []
        for segment in segments:
            for index, member in enumerate(segment.members):
                edges.append(
                    Edge(
                        source_id=member.id,
                        target_id=segment.episode.id,
                        type=EdgeType.PART_OF,
                        weight=max(0.0, min(member.confidence, 1.0)),
                        properties={
                            "position": index,
                            "event_date": member.event_date.date().isoformat()
                            if member.event_date
                            else None,
                        },
                    )
                )
        for left, right in zip(segments, segments[1:]):
            left_end = left.episode.properties["end_date"]
            right_start = right.episode.properties["start_date"]
            gap_days = (
                datetime.fromisoformat(right_start).date() - datetime.fromisoformat(left_end).date()
            ).days
            edges.append(
                Edge(
                    source_id=left.episode.id,
                    target_id=right.episode.id,
                    type=EdgeType.FOLLOWS,
                    weight=1.0,
                    properties={"gap_days": gap_days},
                )
            )
        return edges

    def _episode_id(self, first_member: Node) -> str:
        digest = hashlib.sha1(first_member.id.encode("utf-8")).hexdigest()[:12]
        return f"episode:{self._graph.child_id}:{digest}"

    def _theme(self, members: list[Node]) -> str:
        themes = Counter(self._theme_key(member) for member in members)
        return themes.most_common(1)[0][0]

    def _theme_key(self, node: Node) -> str:
        for key in (
            "place_subtype",
            "place_type",
            "signal_type",
            "category",
            "title",
            "name",
            "value",
        ):
            value = node.properties.get(key)
            if value:
                return str(value).strip().lower().replace(" ", "_")
        return node.type.value.lower()

    def _episode_name(self, theme: str, start: datetime, end: datetime) -> str:
        readable_theme = theme.replace("_", " ")
        if start.date() == end.date():
            return f"{readable_theme} episode on {start.date().isoformat()}"
        return f"{readable_theme} episode {start.date().isoformat()} to {end.date().isoformat()}"

    def _salience(self, confidence: float, event_count: int) -> float:
        return round(min(1.0, confidence + min(0.2, 0.04 * max(event_count - 1, 0))), 3)

    def _max_sensitivity(self, members: list[Node]) -> DataLevel:
        return max(
            (member.sensitivity for member in members), key=lambda level: SENSITIVITY_RANK[level]
        )
