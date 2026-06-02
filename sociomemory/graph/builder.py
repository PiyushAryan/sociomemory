from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sociomemory.graph.nodes import Node, NodeType, DataLevel
from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.memory_graph import MemoryGraph

logger = logging.getLogger(__name__)


class GraphBuilder:

    def __init__(self, graph: MemoryGraph):
        self._graph = graph
        self._child_id = graph.child_id

    def _node(
        self,
        node_type: NodeType,
        properties: dict[str, Any],
        confidence: float = 1.0,
        sensitivity: DataLevel = DataLevel.CONTEXTUAL,
        source_chunk: str | None = None,
        event_date: datetime | None = None,
    ) -> Node:
        return Node(
            child_id=self._child_id,
            type=node_type,
            properties=properties,
            confidence=confidence,
            sensitivity=sensitivity,
            source_chunk=source_chunk,
            event_date=event_date,
        )

    def _edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> Edge:
        return Edge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            weight=weight,
            properties=properties or {},
        )

    # ------------------------------------------------------------------
    # Location enrichment
    # ------------------------------------------------------------------

    def build_location(
        self,
        child_node_id: str,
        neighborhood_name: str,
        city_name: str,
        state_name: str,
        lat: float | None = None,
        lng: float | None = None,
        area_type: str = "urban",
        source_chunk: str | None = None,
    ) -> tuple[list[Node], list[Edge]]:
        nodes: list[Node] = []
        edges: list[Edge] = []

        neighborhood = self._node(
            NodeType.NEIGHBORHOOD,
            {"name": neighborhood_name, "lat": lat, "lng": lng, "area_type": area_type},
            sensitivity=DataLevel.PERSONAL,
            source_chunk=source_chunk,
        )
        city = self._node(NodeType.CITY, {"name": city_name})
        state = self._node(NodeType.STATE, {"name": state_name})

        nodes.extend([neighborhood, city, state])
        edges.extend([
            self._edge(child_node_id, neighborhood.id, EdgeType.LIVES_IN),
            self._edge(neighborhood.id, city.id, EdgeType.LOCATED_IN),
            self._edge(city.id, state.id, EdgeType.LOCATED_IN),
        ])
        return nodes, edges

    # ------------------------------------------------------------------
    # Economic enrichment
    # ------------------------------------------------------------------

    def build_economic(
        self,
        neighborhood_node_id: str,
        area_type: str,
        income_tier: str,
        avg_rent_2bhk: int | None = None,
        avg_sqft_price: int | None = None,
        it_hub: bool = False,
    ) -> tuple[list[Node], list[Edge]]:
        economic = self._node(
            NodeType.ECONOMIC,
            {
                "area_type": area_type,
                "income_tier": income_tier,
                "it_hub": it_hub,
            },
        )
        real_estate = self._node(
            NodeType.REAL_ESTATE,
            {
                "avg_rent_2bhk": avg_rent_2bhk,
                "avg_sqft_price": avg_sqft_price,
            },
            sensitivity=DataLevel.CONTEXTUAL,
        )
        nodes = [economic, real_estate]
        edges = [
            self._edge(neighborhood_node_id, economic.id, EdgeType.HAS_CONTEXT),
            self._edge(neighborhood_node_id, real_estate.id, EdgeType.HAS_CONTEXT),
        ]
        return nodes, edges

    # ------------------------------------------------------------------
    # Safety enrichment
    # ------------------------------------------------------------------

    def build_safety(
        self,
        neighborhood_node_id: str,
        aqi_avg: int | None = None,
        crime_index: float | None = None,
        child_safety_score: float | None = None,
    ) -> tuple[list[Node], list[Edge]]:
        air_quality_score = max(0.0, 1.0 - (aqi_avg or 100) / 300) if aqi_avg else None
        safety = self._node(
            NodeType.SAFETY,
            {
                "aqi_avg": aqi_avg,
                "air_quality": round(air_quality_score, 2) if air_quality_score else None,
                "crime_index": crime_index,
                "child_safety_score": child_safety_score,
                "overall": round(
                    (
                        (air_quality_score or 0.5)
                        + (1.0 - (crime_index or 0.3))
                        + (child_safety_score or 0.7)
                    ) / 3,
                    2,
                ),
            },
        )
        return [safety], [self._edge(neighborhood_node_id, safety.id, EdgeType.HAS_CONTEXT)]

    # ------------------------------------------------------------------
    # Cultural enrichment
    # ------------------------------------------------------------------

    def build_cultural(
        self,
        neighborhood_node_id: str,
        primary_language: str,
        languages: list[str] | None = None,
        cosmopolitan_index: float = 0.5,
        festivals: list[str] | None = None,
    ) -> tuple[list[Node], list[Edge]]:
        cultural = self._node(
            NodeType.CULTURAL,
            {
                "primary_language": primary_language,
                "languages": languages or [primary_language],
                "cosmopolitan": cosmopolitan_index,
                "festivals": festivals or [],
            },
        )
        return [cultural], [self._edge(neighborhood_node_id, cultural.id, EdgeType.HAS_CONTEXT)]

    # ------------------------------------------------------------------
    # Transport enrichment
    # ------------------------------------------------------------------

    def build_transport(
        self,
        neighborhood_node_id: str,
        metro_stations: list[dict] | None = None,
        bus_routes: int = 0,
        connectivity_score: float = 0.5,
    ) -> tuple[list[Node], list[Edge]]:
        transport = self._node(
            NodeType.TRANSPORT,
            {
                "metro_stations": metro_stations or [],
                "bus_routes": bus_routes,
                "connectivity_score": connectivity_score,
            },
        )
        return [transport], [self._edge(neighborhood_node_id, transport.id, EdgeType.HAS_CONTEXT)]

    # ------------------------------------------------------------------
    # Health / nearby places enrichment
    # ------------------------------------------------------------------

    def build_nearby_places(
        self,
        neighborhood_node_id: str,
        places: list[dict],
    ) -> tuple[list[Node], list[Edge]]:
        nodes: list[Node] = []
        edges: list[Edge] = []
        for place_data in places:
            place = self._node(
                NodeType.PLACE,
                {
                    "name": place_data.get("name"),
                    "place_type": place_data.get("type"),
                    "distance_km": place_data.get("distance_km"),
                    "child_friendly": place_data.get("child_friendly", True),
                },
            )
            nodes.append(place)
            edges.append(
                self._edge(
                    neighborhood_node_id,
                    place.id,
                    EdgeType.NEAR_TO,
                    weight=round(1.0 / max(0.1, place_data.get("distance_km", 1.0)), 3),
                    properties={"distance_km": place_data.get("distance_km")},
                )
            )
        return nodes, edges

    # ------------------------------------------------------------------
    # School enrichment
    # ------------------------------------------------------------------

    def build_school(
        self,
        child_node_id: str,
        school_name: str,
        board: str = "",
        medium: str = "English",
        fee_yearly: int | None = None,
        has_inclusion_program: bool = False,
        source_chunk: str | None = None,
    ) -> tuple[list[Node], list[Edge]]:
        fee_tier = "high" if (fee_yearly or 0) > 150000 else "middle" if (fee_yearly or 0) > 50000 else "low"
        school = self._node(
            NodeType.SCHOOL,
            {
                "name": school_name,
                "board": board,
                "medium": medium,
                "fee_yearly": fee_yearly,
                "fee_tier": fee_tier,
                "has_inclusion_program": has_inclusion_program,
            },
            sensitivity=DataLevel.PERSONAL,
            source_chunk=source_chunk,
        )
        return [school], [self._edge(child_node_id, school.id, EdgeType.ATTENDS)]

    # ------------------------------------------------------------------
    # Visit enrichment (behavioral place intelligence)
    # ------------------------------------------------------------------

    def build_visit(
        self,
        child_node_id: str,
        place_name: str,
        place_type: str,
        place_subtype: str | None = None,
        event_date: datetime | None = None,
        mood: str | None = None,
        sensory_notes: str | None = None,
        source_chunk: str | None = None,
        confidence: float = 0.8,
    ) -> tuple[list[Node], list[Edge]]:
        nodes: list[Node] = []
        edges: list[Edge] = []

        # Visit event node
        visit = self._node(
            NodeType.VISIT,
            {
                "place_name": place_name,
                "place_type": place_type,
                "place_subtype": place_subtype,
                "mood": mood,
                "sensory_notes": sensory_notes,
            },
            confidence=confidence,
            sensitivity=DataLevel.PERSONAL,
            source_chunk=source_chunk,
            event_date=event_date,
        )
        # Place node
        place = self._node(
            NodeType.PLACE,
            {
                "name": place_name,
                "place_type": place_type,
                "place_subtype": place_subtype or "",
            },
        )
        nodes.extend([visit, place])
        edges.extend([
            self._edge(child_node_id, visit.id, EdgeType.VISITED),
            self._edge(visit.id, place.id, EdgeType.AT),
        ])

        # Identity inference from place type
        inferred = self._infer_from_visit(place_type, place_subtype, visit.id, confidence)
        nodes.extend(inferred[0])
        edges.extend(inferred[1])

        return nodes, edges

    def _infer_from_visit(
        self,
        place_type: str,
        place_subtype: str | None,
        visit_node_id: str,
        base_confidence: float,
    ) -> tuple[list[Node], list[Edge]]:
        nodes: list[Node] = []
        edges: list[Edge] = []

        RELIGIOUS_MAP = {
            ("temple", "iskcon"): ("vaishnavism", "krishna_devotee", ["janmashtami", "rath_yatra"]),
            ("temple", "iskcon_temple"): ("vaishnavism", "krishna_devotee", ["janmashtami"]),
            ("temple", None): ("hinduism", "hindu", ["diwali", "navratri"]),
            ("mosque", None): ("islam", "muslim", ["eid", "ramadan"]),
            ("church", None): ("christianity", "christian", ["christmas", "easter"]),
            ("gurudwara", None): ("sikhism", "sikh", ["baisakhi", "gurpurab"]),
        }

        key = (place_type.lower(), place_subtype.lower() if place_subtype else None)
        if key in RELIGIOUS_MAP or (place_type.lower(), None) in RELIGIOUS_MAP:
            tradition, identity, festivals = RELIGIOUS_MAP.get(key) or RELIGIOUS_MAP.get((place_type.lower(), None))
            religious = self._node(
                NodeType.RELIGIOUS,
                {"tradition": tradition, "identity": identity, "festivals": festivals},
                confidence=base_confidence * 0.7,
            )
            nodes.append(religious)
            edges.append(self._edge(visit_node_id, religious.id, EdgeType.INDICATES,
                                    weight=base_confidence * 0.7))

        LIFESTYLE_MAP = {
            "mountain": ("outdoor_active", "adventure_therapy"),
            "hill_station": ("outdoor_active", "adventure_therapy"),
            "beach": ("outdoor_active", None),
            "snow_park": ("outdoor_active", "cold_tolerant"),
            "water_park": ("outdoor_active", None),
            "park": ("outdoor_active", None),
            "playground": ("outdoor_active", None),
        }
        if place_type.lower() in LIFESTYLE_MAP:
            lifestyle_tag, sensory_tag = LIFESTYLE_MAP[place_type.lower()]
            lifestyle = self._node(
                NodeType.LIFESTYLE,
                {"tag": lifestyle_tag, "outdoor_active": True},
                confidence=base_confidence * 0.8,
            )
            nodes.append(lifestyle)
            edges.append(self._edge(visit_node_id, lifestyle.id, EdgeType.INDICATES,
                                    weight=base_confidence * 0.8))
            if sensory_tag:
                sensory = self._node(
                    NodeType.SENSORY_EVIDENCE,
                    {"stimulus": sensory_tag.replace("_tolerant", ""),
                     "response": "tolerated", "tag": sensory_tag},
                    confidence=base_confidence * 0.6,
                )
                nodes.append(sensory)
                edges.append(self._edge(visit_node_id, sensory.id, EdgeType.INDICATES,
                                        weight=base_confidence * 0.6))

        return nodes, edges

    # ------------------------------------------------------------------
    # Parent / employer
    # ------------------------------------------------------------------

    def build_parent(
        self,
        child_node_id: str,
        parent_name: str | None = None,
        profession: str | None = None,
        employer_name: str | None = None,
        industry: str | None = None,
        source_chunk: str | None = None,
    ) -> tuple[list[Node], list[Edge]]:
        nodes: list[Node] = []
        edges: list[Edge] = []

        parent = self._node(
            NodeType.PARENT,
            {"name": parent_name or ""},
            sensitivity=DataLevel.PERSONAL,
            source_chunk=source_chunk,
        )
        nodes.append(parent)
        edges.append(self._edge(parent.id, child_node_id, EdgeType.PARENT_OF))

        if employer_name or profession:
            employer = self._node(
                NodeType.EMPLOYER,
                {
                    "name": employer_name or "",
                    "profession": profession or "",
                    "industry": industry or "",
                },
                source_chunk=source_chunk,
            )
            nodes.append(employer)
            edges.append(self._edge(parent.id, employer.id, EdgeType.WORKS_AT))

        return nodes, edges

    # ------------------------------------------------------------------
    # Income node (derived)
    # ------------------------------------------------------------------

    def build_income_node(
        self,
        input_node_ids: list[str],
        bracket: str,
        monthly_range: tuple[int, int],
        confidence: float,
        convergence_score: float,
        affordability_index: float,
        signals_used: list[str],
    ) -> tuple[list[Node], list[Edge]]:
        income = self._node(
            NodeType.INCOME,
            {
                "bracket": bracket,
                "monthly_min": monthly_range[0],
                "monthly_max": monthly_range[1],
                "convergence_score": convergence_score,
                "affordability_index": affordability_index,
                "signals_used": signals_used,
            },
            confidence=confidence,
            sensitivity=DataLevel.SENSITIVE,
        )
        edges = [
            self._edge(src_id, income.id, EdgeType.DERIVES,
                       weight=confidence)
            for src_id in input_node_ids
        ]
        return [income], edges
