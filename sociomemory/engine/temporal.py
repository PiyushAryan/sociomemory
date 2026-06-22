from __future__ import annotations

import logging
import math
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from sociomemory.graph.nodes import Node, NodeType
from sociomemory.time import utc_now

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph

logger = logging.getLogger(__name__)


class TemporalEngine:
    def __init__(self, graph: MemoryGraph):
        self._graph = graph

    async def get_events_in_period(
        self, start: datetime, end: datetime, node_type: NodeType | None = None
    ) -> list[Node]:
        return await self._graph.query_by_event_date(start, end, node_type)

    async def get_last_summer_events(self) -> list[Node]:
        now = utc_now()
        year = now.year - 1
        return await self.get_events_in_period(datetime(year, 6, 1), datetime(year, 8, 31))

    async def get_visit_timeline(self) -> list[Node]:
        return await self._graph.get_timeline()

    async def detect_visit_patterns(self) -> list[dict]:
        visits = await self._graph.get_nodes_by_type(NodeType.VISIT)
        type_counts: Counter = Counter()
        for v in visits:
            pt = v.properties.get("place_type", "")
            if pt:
                type_counts[pt] += 1

        total = len(visits)
        patterns = []
        for place_type, count in type_counts.most_common():
            if count >= 2:
                patterns.append(
                    {
                        "pattern": f"Visits {place_type} frequently",
                        "place_type": place_type,
                        "visit_count": count,
                        "frequency": round(count / max(total, 1), 2),
                        "confidence": min(0.95, 0.3 + 0.3 * math.log1p(count)),
                        "insight": self._pattern_insight(place_type, count),
                    }
                )
        return patterns

    def _pattern_insight(self, place_type: str, count: int) -> str:
        INSIGHTS = {
            "temple": f"Religious engagement confirmed ({count} visits).",
            "mosque": f"Muslim family likely ({count} visits). Halal dietary context.",
            "church": f"Christian context ({count} visits). Holiday scheduling applies.",
            "gurudwara": f"Sikh community ({count} visits). Langar community engagement.",
            "mountain": f"Outdoor-active family ({count} trips). Adventure therapy viable.",
            "beach": f"Water/outdoor comfort ({count} visits). Aquatic therapy possibilities.",
            "park": f"Regular outdoor activity ({count} visits). Gross motor goals compatible.",
            "water_park": "Water comfort + crowd tolerance. Aqua/group therapy viable.",
            "mall": "Crowd tolerance confirmed. Group therapy settings acceptable.",
        }
        return INSIGHTS.get(place_type, f"{count} visits to {place_type} noted.")

    async def detect_freshness_decay(self, node_ids: list[str]) -> dict[str, float]:
        scores = {}
        now = utc_now()
        for nid in node_ids:
            node = await self._graph.get_node(nid)
            if not node:
                scores[nid] = 0.0
                continue
            age_days = (now - node.updated_at).days
            if age_days <= 30:
                score = 1.0
            elif age_days <= 90:
                score = 1.0 - 0.5 * (age_days - 30) / 60
            elif age_days <= 365:
                score = 0.5 - 0.4 * (age_days - 90) / 275
            else:
                score = 0.1
            scores[nid] = round(max(0.0, score), 3)
        return scores
