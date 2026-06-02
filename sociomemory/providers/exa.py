from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from sociomemory.graph.builder import GraphBuilder
from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.nodes import DataLevel, Node, NodeType
from sociomemory.models.signals import Signal, SignalType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.llm.base import BaseLLM
    from sociomemory.storage.cache import SQLiteCache

logger = logging.getLogger(__name__)


class ExaLocationProvider:

    provider_name = "exa_location"
    requires_network = True

    QUERIES = [
        "{location} civic political climate governance quality 2024 2025",
        "{location} therapy center autism special education occupational therapy",
        "{location} income real estate rent middle class lifestyle 2024",
        "{location} cultural language festivals community demographics",
        "{location} safety AQI air quality crime index child safety",
    ]

    EXTRACT_PROMPT = """Extract structured context for location '{location}' from the web search results below.
Return ONLY valid JSON with these fields (use null if not found):
{{
  "area_type": "urban_affluent|urban_middle|semi_urban|rural",
  "income_tier": "low|lower_middle|middle|upper_middle|high",
  "avg_rent_2bhk": <integer rupees per month or null>,
  "political_climate": "stable|moderate|volatile",
  "strike_frequency": "low|moderate|high",
  "public_services_quality": <float 0-1 or null>,
  "ngo_density": "low|moderate|high",
  "therapy_centers": [
    {{"name": "...", "type": "occupational|speech|aba|general", "distance_km": null}}
  ],
  "primary_language": "...",
  "languages": ["..."],
  "aqi_avg": <integer or null>,
  "child_safety_score": <float 0-1 or null>,
  "connectivity_score": <float 0-1 or null>,
  "civic_notes": "one sentence summary"
}}

Search results:
{content}

JSON:"""

    def __init__(self, api_key: str, llm: "BaseLLM", cache: "SQLiteCache"):
        self._api_key = api_key
        self._llm = llm
        self._cache = cache
        self._exa = None

    def _get_exa(self):
        if self._exa is None:
            try:
                from exa_py import Exa  # type: ignore
                self._exa = Exa(api_key=self._api_key)
            except ImportError:
                raise ImportError("exa-py is required: pip install exa-py")
        return self._exa

    async def enrich(self, signal: Signal, graph: "MemoryGraph") -> tuple[list[Node], list[Edge]]:
        if signal.signal_type != SignalType.LOCATION:
            return [], []

        location = signal.extracted_value.strip()
        cache_key = f"exa_location:{location.lower()}"

        # Check cache first
        cached = self._cache.get(cache_key)
        if cached:
            logger.debug("Exa cache hit for %s", location)
            return await self._build_from_data(cached, location, signal, graph)

        # Fetch from Exa
        content = await self._fetch_exa_content(location)
        if not content:
            return [], []

        # LLM extract structured data
        prompt = self.EXTRACT_PROMPT.format(location=location, content=content[:4000])
        try:
            raw = await self._llm.complete(prompt, temperature=0.1)
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
        except Exception as exc:
            logger.error("Exa LLM extraction failed for %s: %s", location, exc)
            return [], []

        # Cache for 24h
        self._cache.set(cache_key, data, provider="exa", ttl_hours=24)

        return await self._build_from_data(data, location, signal, graph)

    async def _fetch_exa_content(self, location: str) -> str:
        exa = self._get_exa()
        content_parts = []
        for query_template in self.QUERIES:
            query = query_template.format(location=location)
            try:
                results = exa.search_and_contents(
                    query,
                    num_results=3,
                    text={"max_characters": 600},
                )
                for r in results.results:
                    if r.text:
                        content_parts.append(f"[{r.title}]\n{r.text}")
            except Exception as exc:
                logger.warning("Exa query failed (%s): %s", query[:50], exc)

        return "\n\n".join(content_parts)

    async def _build_from_data(
        self,
        data: dict,
        location: str,
        signal: Signal,
        graph: "MemoryGraph",
    ) -> tuple[list[Node], list[Edge]]:
        builder = GraphBuilder(graph)
        nodes: list[Node] = []
        edges: list[Edge] = []

        # Get child and neighborhood nodes
        from sociomemory.graph.nodes import NodeType
        child_nodes = await graph.get_nodes_by_type(NodeType.CHILD)
        hood_nodes = await graph.get_nodes_by_type(NodeType.NEIGHBORHOOD)

        if not child_nodes:
            return [], []

        child_id = child_nodes[0].id
        hood_id = hood_nodes[0].id if hood_nodes else child_id

        # Build/update location node if area_type available
        if data.get("area_type") or data.get("avg_rent_2bhk"):
            econ_nodes, econ_edges = builder.build_economic(
                neighborhood_node_id=hood_id,
                area_type=data.get("area_type", "urban"),
                income_tier=data.get("income_tier", "middle"),
                avg_rent_2bhk=data.get("avg_rent_2bhk"),
                it_hub=False,
            )
            nodes.extend(econ_nodes)
            edges.extend(econ_edges)

        # Cultural context
        if data.get("primary_language"):
            cult_nodes, cult_edges = builder.build_cultural(
                neighborhood_node_id=hood_id,
                primary_language=data["primary_language"],
                languages=data.get("languages", [data["primary_language"]]),
            )
            nodes.extend(cult_nodes)
            edges.extend(cult_edges)

        # Safety context
        if data.get("aqi_avg") or data.get("child_safety_score"):
            safety_nodes, safety_edges = builder.build_safety(
                neighborhood_node_id=hood_id,
                aqi_avg=data.get("aqi_avg"),
                child_safety_score=data.get("child_safety_score"),
            )
            nodes.extend(safety_nodes)
            edges.extend(safety_edges)

        # Transport
        if data.get("connectivity_score"):
            transport_nodes, transport_edges = builder.build_transport(
                neighborhood_node_id=hood_id,
                connectivity_score=data["connectivity_score"],
            )
            nodes.extend(transport_nodes)
            edges.extend(transport_edges)

        # Civic node (new: political climate, NGO density, civic quality)
        civic_props: dict[str, Any] = {}
        for key in ("political_climate", "strike_frequency", "public_services_quality",
                    "ngo_density", "civic_notes"):
            if data.get(key) is not None:
                civic_props[key] = data[key]

        if civic_props:
            civic_node = Node(
                child_id=graph.child_id,
                type=NodeType.CIVIC,
                properties=civic_props,
                confidence=0.7,
                sensitivity=DataLevel.CONTEXTUAL,
                source_chunk=signal.raw_text,
            )
            nodes.append(civic_node)
            edges.append(Edge(
                source_id=hood_id,
                target_id=civic_node.id,
                type=EdgeType.HAS_CONTEXT,
                weight=0.7,
            ))

        # Nearby therapy centers
        therapy_centers = data.get("therapy_centers", [])
        if therapy_centers:
            places = [
                {
                    "name": tc["name"],
                    "type": f"therapy_{tc.get('type', 'general')}",
                    "distance_km": tc.get("distance_km") or 3.0,
                    "child_friendly": True,
                }
                for tc in therapy_centers[:5]
            ]
            place_nodes, place_edges = builder.build_nearby_places(
                neighborhood_node_id=hood_id,
                places=places,
            )
            nodes.extend(place_nodes)
            edges.extend(place_edges)

        logger.info(
            "Exa enriched %s: %d nodes, %d edges (civic=%s, therapy_centers=%d)",
            location, len(nodes), len(edges),
            civic_props.get("political_climate", "unknown"),
            len(therapy_centers),
        )
        return nodes, edges

    async def health_check(self) -> bool:
        try:
            exa = self._get_exa()
            results = exa.search("test", num_results=1)
            return bool(results)
        except Exception:
            return False
