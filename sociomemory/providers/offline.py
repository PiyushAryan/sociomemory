from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sociomemory.graph.builder import GraphBuilder
from sociomemory.graph.edges import Edge
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.models.signals import Signal, SignalType

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


class OfflineLocationProvider:
    """Offline location enrichment from bundled india_cities.json."""

    provider_name = "offline_location"
    requires_network = False

    def __init__(self):
        self._cities: list = _load_json("india_cities.json") if isinstance(_load_json("india_cities.json"), list) else []
        self._real_estate: dict = _load_json("india_real_estate.json")
        self._cultural: dict = _load_json("cultural_regions.json")

    async def enrich(self, signal: Signal, graph) -> tuple[list[Node], list[Edge]]:
        if signal.signal_type != SignalType.LOCATION:
            return [], []

        city_data = self._find_city(signal.extracted_value.strip().lower())
        if not city_data:
            return [], []

        child_nodes = await graph.get_nodes_by_type(NodeType.CHILD)
        if not child_nodes:
            return [], []

        builder = GraphBuilder(graph)
        neighborhood = city_data.get("neighborhood", signal.extracted_value.title())
        city = city_data.get("city", "Unknown")
        state = city_data.get("state", "Unknown")

        nodes, edges = builder.build_location(
            child_node_id=child_nodes[0].id,
            neighborhood_name=neighborhood,
            city_name=city,
            state_name=state,
            lat=city_data.get("lat"),
            lng=city_data.get("lng"),
            area_type=city_data.get("area_type", "urban"),
            source_chunk=signal.raw_text,
        )

        if nodes:
            neighborhood_node = nodes[0]
            area_key = neighborhood.lower().replace(" ", "_")
            re_data = self._real_estate.get(area_key, {})
            if re_data:
                econ_nodes, econ_edges = builder.build_economic(
                    neighborhood_node_id=neighborhood_node.id,
                    area_type=re_data.get("area_type", "urban"),
                    income_tier=re_data.get("income_tier", "middle"),
                    avg_rent_2bhk=re_data.get("avg_rent_2bhk"),
                    avg_sqft_price=re_data.get("avg_sqft_price"),
                    it_hub=re_data.get("it_hub", False),
                )
                nodes.extend(econ_nodes)
                edges.extend(econ_edges)

            state_key = state.lower().replace(" ", "_")
            cultural_data = self._cultural.get(state_key, {})
            if cultural_data:
                cult_nodes, cult_edges = builder.build_cultural(
                    neighborhood_node_id=neighborhood_node.id,
                    primary_language=cultural_data.get("primary_language", "Hindi"),
                    languages=cultural_data.get("languages", []),
                    cosmopolitan_index=cultural_data.get("cosmopolitan_index", 0.5),
                    festivals=cultural_data.get("festivals", []),
                )
                nodes.extend(cult_nodes)
                edges.extend(cult_edges)

        return nodes, edges

    def _find_city(self, query: str) -> dict | None:
        query_parts = [q.strip() for q in query.replace(",", " ").split() if len(q) > 3]
        for entry in self._cities:
            city = entry.get("city", "").lower()
            neighborhood = entry.get("neighborhood", "").lower()
            if any(p in city or p in neighborhood for p in query_parts):
                return entry
        return None

    async def health_check(self) -> bool:
        return DATA_DIR.exists()


class OfflineSchoolProvider:
    """Offline school enrichment from bundled school_boards.json."""

    provider_name = "offline_school"
    requires_network = False

    def __init__(self):
        self._schools: dict = _load_json("school_boards.json")

    async def enrich(self, signal: Signal, graph) -> tuple[list[Node], list[Edge]]:
        if signal.signal_type != SignalType.SCHOOL:
            return [], []

        child_nodes = await graph.get_nodes_by_type(NodeType.CHILD)
        if not child_nodes:
            return [], []

        builder = GraphBuilder(graph)
        school_name = signal.extracted_value.strip()
        school_data = self._find_school(school_name)

        nodes, edges = builder.build_school(
            child_node_id=child_nodes[0].id,
            school_name=school_name,
            board=school_data.get("board", ""),
            medium=school_data.get("medium", "English"),
            fee_yearly=school_data.get("fee_yearly"),
            has_inclusion_program=school_data.get("has_inclusion_program", False),
            source_chunk=signal.raw_text,
        )
        return nodes, edges

    def _find_school(self, name: str) -> dict:
        name_lower = name.lower()
        for key, data in self._schools.items():
            if key.lower() in name_lower or name_lower in key.lower():
                return data
        if "dps" in name_lower or "delhi public" in name_lower:
            return {"board": "CBSE", "medium": "English", "fee_yearly": 200000}
        if "kendriya vidyalaya" in name_lower or "kv " in name_lower:
            return {"board": "CBSE", "medium": "English", "fee_yearly": 15000}
        if "international" in name_lower:
            return {"board": "IB", "medium": "English", "fee_yearly": 500000}
        return {}

    async def health_check(self) -> bool:
        return True
