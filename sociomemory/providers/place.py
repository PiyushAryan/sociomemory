from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from sociomemory.graph.edges import Edge, EdgeType
from sociomemory.graph.nodes import DataLevel, Node, NodeType
from sociomemory.models.signals import Signal, SignalType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.llm.base import BaseLLM
    from sociomemory.storage.cache import SQLiteCache

logger = logging.getLogger(__name__)


class PlaceEnrichmentProvider:

    provider_name = "place_web_enrichment"
    requires_network = True

    EXTRACT_PROMPT = """Extract structured facts about the public place below from the web results.
Place mentioned: "{place}" (type: {place_type}) near {locality}.
Return ONLY valid JSON (use null when unknown):
{{
  "full_name": "canonical name of the specific place, or null",
  "category": "temple|mosque|church|metro_station|restaurant|cafe|park|mall|museum|hospital|library|market|stadium|cinema|other",
  "locality": "area/neighborhood name or null",
  "city": "city name or null",
  "summary": "one factual sentence about this place",
  "tags": ["short", "descriptors"],
  "cuisine": "for restaurants/cafes only, e.g. south_indian|vegetarian, else null",
  "deity_or_tradition": "for temples/religious places only, else null"
}}

Web results:
{content}

JSON:"""

    def __init__(self, llm: "BaseLLM", cache: "SQLiteCache", exa_api_key: str = ""):
        self._llm = llm
        self._cache = cache
        self._exa_api_key = exa_api_key
        self._exa = None

    def _get_exa(self):
        if not self._exa_api_key:
            return None
        if self._exa is None:
            try:
                from exa_py import Exa  # type: ignore
                self._exa = Exa(api_key=self._exa_api_key)
            except ImportError:
                logger.warning("exa-py not installed; place enrichment uses OpenAI web search only")
                self._exa_api_key = ""
                return None
        return self._exa

    async def enrich(self, signal: Signal, graph: "MemoryGraph") -> tuple[list[Node], list[Edge]]:
        if signal.signal_type != SignalType.VISIT:
            return [], []

        place = await self._find_place(signal, graph)
        if place is None or place.properties.get("web_enriched"):
            return [], []

        hood = await self._first(graph, NodeType.NEIGHBORHOOD)
        city = await self._first(graph, NodeType.CITY)
        locality = " ".join(
            part for part in (
                hood.properties.get("name") if hood else None,
                city.properties.get("name") if city else None,
            ) if part
        ) or "India"

        place_label = place.properties.get("name") or signal.extracted_value
        place_type = place.properties.get("place_type") or signal.place_type or ""

        cache_key = f"place:{place_label.lower()}:{place_type}:{locality.lower()}"
        data = self._cache.get(cache_key)
        if not data:
            content = await self._gather(place_label, place_type, locality)
            if not content.strip():
                return [], []
            data = await self._extract(place_label, place_type, locality, content)
            if not data:
                return [], []
            self._cache.set(cache_key, data, provider="place_web", ttl_hours=24)

        return self._build(place, hood, data)

    async def _find_place(self, signal: Signal, graph: "MemoryGraph") -> Node | None:
        places = await graph.get_nodes_by_type(NodeType.PLACE)
        if not places:
            return None
        target_name = (signal.place_name or signal.extracted_value or "").strip().lower()
        target_type = (signal.place_type or "").strip().lower()

        def score(node: Node) -> tuple[int, str]:
            name = str(node.properties.get("name", "")).lower()
            ptype = str(node.properties.get("place_type", "")).lower()
            match = (target_name and name == target_name) or (target_type and ptype == target_type)
            return (1 if match else 0, node.created_at.isoformat())

        candidates = [p for p in places if not p.properties.get("web_enriched")]
        if not candidates:
            return None
        return max(candidates, key=score)

    async def _gather(self, place: str, place_type: str, locality: str) -> str:
        query = f"{place} {place_type} in {locality}".strip()
        parts: list[str] = []

        exa = self._get_exa()
        if exa is not None:
            try:
                results = exa.search_and_contents(query, num_results=3, text={"max_characters": 600})
                for r in results.results:
                    if r.text:
                        parts.append(f"[exa:{r.title}]\n{r.text}")
            except Exception as exc:
                logger.warning("Exa place query failed (%s): %s", query[:50], exc)

        web_search = getattr(self._llm, "web_search", None)
        if callable(web_search):
            try:
                answer = await web_search(
                    f"Describe the public place: {query}. Include its area, category, and what it is known for."
                )
                if answer:
                    parts.append(f"[openai_web]\n{answer}")
            except Exception as exc:
                logger.warning("OpenAI web search failed (%s): %s", query[:50], exc)

        return "\n\n".join(parts)

    async def _extract(self, place: str, place_type: str, locality: str, content: str) -> dict | None:
        prompt = self.EXTRACT_PROMPT.format(
            place=place, place_type=place_type or "unknown", locality=locality, content=content[:4000]
        )
        try:
            raw = await self._llm.complete(prompt, temperature=0.1)
            raw = raw.strip().strip("```json").strip("```").strip()
            return json.loads(raw)
        except Exception as exc:
            logger.error("Place extraction failed for %s: %s", place, exc)
            return None

    def _build(self, place: Node, hood: Node | None, data: dict) -> tuple[list[Node], list[Edge]]:
        enriched_props: dict[str, Any] = dict(place.properties)
        for key in ("category", "summary", "cuisine", "deity_or_tradition"):
            value = data.get(key)
            if value is not None:
                enriched_props[key] = value
        if data.get("full_name"):
            enriched_props["full_name"] = data["full_name"]
        if isinstance(data.get("tags"), list) and data["tags"]:
            enriched_props["tags"] = data["tags"][:8]
        for key in ("locality", "city"):
            if data.get(key):
                enriched_props.setdefault(key, data[key])
        enriched_props["web_enriched"] = True
        enriched_props["enrichment_sources"] = "exa+openai_web"

        # Same id => MERGE_NODE updates the existing Place node in place.
        enriched_place = Node(
            id=place.id,
            child_id=place.child_id,
            type=NodeType.PLACE,
            properties=enriched_props,
            confidence=place.confidence,
            sensitivity=place.sensitivity,
            event_date=place.event_date,
            source_chunk=place.source_chunk,
        )
        edges: list[Edge] = []
        if hood is not None:
            edges.append(Edge(
                source_id=place.id,
                target_id=hood.id,
                type=EdgeType.LOCATED_IN,
                weight=0.7,
                properties={"inferred": "web_enrichment"},
            ))
        logger.info("Web-enriched place %s -> %s", place.properties.get("name"), data.get("category"))
        return [enriched_place], edges

    async def _first(self, graph: "MemoryGraph", node_type: NodeType) -> Node | None:
        nodes = await graph.get_nodes_by_type(node_type)
        return nodes[0] if nodes else None

    async def health_check(self) -> bool:
        return True
