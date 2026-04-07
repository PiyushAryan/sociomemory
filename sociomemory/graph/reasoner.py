from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sociomemory.engine.behavioral import BehavioralInference
from sociomemory.engine.income import IncomeEstimator
from sociomemory.engine.tradeoff import TradeOffDetector
from sociomemory.graph.nodes import Node, NodeType
from sociomemory.models.coaching import CoachingImplication, IncomeEstimate, TradeOff

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class GraphReasoner:
    """High-level reasoning interface over the MemoryGraph."""

    def __init__(self, graph: "MemoryGraph", llm: "BaseLLM | None" = None):
        self._graph = graph
        self._llm = llm
        self._income = IncomeEstimator(graph)
        self._behavioral = BehavioralInference(graph)
        self._tradeoff = TradeOffDetector(graph, llm)

    async def infer_income(self) -> IncomeEstimate | None:
        return await self._income.estimate()

    async def detect_tradeoffs(self) -> list[TradeOff]:
        return await self._tradeoff.detect()

    async def get_behavioral_identity(self) -> dict:
        return await self._behavioral.infer_identity()

    async def get_therapy_opportunities(self) -> list[dict]:
        return await self._behavioral.suggest_therapy_opportunities()

    async def find_nearby_resources(self, resource_type: str, max_distance_km: float = 5.0) -> list[Node]:
        place_nodes = await self._graph.get_nodes_by_type(NodeType.PLACE)
        results = [
            n for n in place_nodes
            if resource_type.lower() in (n.properties.get("place_type") or "").lower()
            and float(n.properties.get("distance_km", 999)) <= max_distance_km
        ]
        results.sort(key=lambda n: n.properties.get("distance_km", 999))
        return results

    async def generate_coaching_context(self) -> str:
        lines = ["## Socioeconomic Context (Graph-Derived)"]

        income = await self.infer_income()
        if income:
            lines.append(
                f"- Income: {income.bracket} "
                f"(₹{income.monthly_range[0]:,}–{income.monthly_range[1]:,}/mo, "
                f"confidence {income.confidence:.0%})"
            )

        hood_nodes = await self._graph.get_nodes_by_type(NodeType.NEIGHBORHOOD)
        if hood_nodes:
            n = hood_nodes[0]
            lines.append(f"- Area: {n.properties.get('name', 'unknown')} ({n.properties.get('area_type', '')})")

        safety_nodes = await self._graph.get_nodes_by_type(NodeType.SAFETY)
        if safety_nodes:
            aqi = safety_nodes[0].properties.get("aqi_avg")
            if aqi:
                lines.append(f"- AQI: {aqi} ({'poor' if aqi > 150 else 'moderate' if aqi > 100 else 'good'})")

        cultural_nodes = await self._graph.get_nodes_by_type(NodeType.CULTURAL)
        if cultural_nodes:
            lang = cultural_nodes[0].properties.get("primary_language")
            if lang:
                lines.append(f"- Primary language: {lang}")

        identity = await self.get_behavioral_identity()
        if identity.get("lifestyle"):
            lines.append(f"- Lifestyle: {', '.join(identity['lifestyle'].keys())}")
        if identity.get("religious"):
            rel = identity["religious"]
            lines.append(f"- Religious: {rel['identity']} ({rel['confidence']:.0%})")

        opps = await self.get_therapy_opportunities()
        if opps:
            lines.append(f"- Therapy opportunities: {', '.join(o['type'].replace('_', ' ') for o in opps[:3])}")

        tradeoffs = await self.detect_tradeoffs()
        for to in tradeoffs[:2]:
            lines.append(f"- Trade-off ({to.dimension}): {to.resolution or 'see positive/negative signals'}")

        return "\n".join(lines)

    async def explain_node(self, node_id: str) -> str:
        node = await self._graph.get_node(node_id)
        if not node:
            return f"Node {node_id} not found."
        lines = [f"Node: {node.type.value} (confidence {node.confidence:.0%})"]
        if node.source_chunk:
            lines.append(f"Source: '{node.source_chunk}'")
        provenance = await self._graph.get_provenance(node_id)
        if provenance:
            lines.append("Derived from:")
            for p in provenance[:5]:
                chunk = p.get("source_chunk", "")
                if chunk:
                    lines.append(f"  - '{chunk}' ({p.get('document_date', '')})")
        return "\n".join(lines)

    async def identify_gaps(self) -> list[str]:
        all_nodes = await self._get_all_nodes()
        present = {n.type for n in all_nodes}
        gaps = []
        if NodeType.NEIGHBORHOOD not in present:
            gaps.append("location (ask: 'Where do you live?')")
        if NodeType.SCHOOL not in present:
            gaps.append("school (ask: 'Which school does the child attend?')")
        if NodeType.EMPLOYER not in present:
            gaps.append("parent profession (ask: 'What does your parent do for work?')")
        if NodeType.VISIT not in present:
            gaps.append("activities (ask: 'Where does the family like to go?')")
        return gaps

    async def _get_all_nodes(self) -> list[Node]:
        from sociomemory.graph import cypher as Q
        records = await self._graph._neo4j.run(Q.GET_ALL_NODES, child_id=self._graph.child_id)
        return [self._graph._parse_node(r["n"]) for r in records if r.get("n")]
