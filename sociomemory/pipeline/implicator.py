from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sociomemory.graph.nodes import NodeType
from sociomemory.models.coaching import CoachingImplication

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph
    from sociomemory.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class CoachingImplicator:
    """Traverse the graph to produce actionable coaching implications with provenance."""

    def __init__(self, graph: "MemoryGraph", llm: "BaseLLM | None" = None):
        self._graph = graph
        self._llm = llm

    async def generate(self) -> list[CoachingImplication]:
        implications: list[CoachingImplication] = []

        # Pull IMPLICATION nodes already in the graph
        impl_nodes = await self._graph.get_nodes_by_type(NodeType.IMPLICATION)
        for node in impl_nodes:
            text = node.properties.get("text", "")
            if text:
                provenance = await self._graph.get_provenance(node.id)
                source_chunks = [p.get("source_chunk", "") for p in provenance if p.get("source_chunk")]
                implications.append(CoachingImplication(
                    category=node.properties.get("category", "general"),
                    implication=text,
                    strength=node.confidence,
                    graph_path=[node.id],
                    source_chunks=source_chunks,
                    metadata=node.properties,
                ))

        # Rule-based implications from graph state
        implications.extend(await self._rule_based_implications())

        # Optional LLM synthesis
        if self._llm and implications:
            implications = await self._enrich_with_llm(implications)

        implications.sort(key=lambda x: x.strength, reverse=True)
        return implications

    async def _rule_based_implications(self) -> list[CoachingImplication]:
        results = []

        safety_nodes = await self._graph.get_nodes_by_type(NodeType.SAFETY)
        for safety in safety_nodes:
            aqi = safety.properties.get("aqi_avg", 0)
            if aqi and aqi > 150:
                results.append(CoachingImplication(
                    category="activity",
                    implication="AQI is poor — prefer indoor activities or early morning outdoor sessions.",
                    strength=min(0.9, aqi / 300),
                    graph_path=[safety.id],
                    metadata={"aqi": aqi, "dimension": "outdoor", "direction": "negative"},
                ))

        income_nodes = await self._graph.get_nodes_by_type(NodeType.INCOME)
        for income in income_nodes:
            bracket = income.properties.get("bracket", "")
            affordability = income.properties.get("affordability_index", 0.5)
            if bracket in ("upper_middle", "high") and affordability > 0.7:
                results.append(CoachingImplication(
                    category="resource",
                    implication="Family can likely afford professional OT/SLP. Recommend specialist referral.",
                    strength=affordability,
                    graph_path=[income.id],
                    metadata={"bracket": bracket, "dimension": "affordability", "direction": "positive"},
                ))
            elif bracket in ("low", "lower_middle") and affordability < 0.35:
                results.append(CoachingImplication(
                    category="resource",
                    implication="Limited therapy budget. Focus on AI coaching + free/NGO resources.",
                    strength=1.0 - affordability,
                    graph_path=[income.id],
                    metadata={"bracket": bracket, "dimension": "affordability", "direction": "negative"},
                ))

        cultural_nodes = await self._graph.get_nodes_by_type(NodeType.CULTURAL)
        for cultural in cultural_nodes:
            lang = cultural.properties.get("primary_language", "")
            if lang and lang.lower() not in ("english",):
                results.append(CoachingImplication(
                    category="tone",
                    implication=f"Use {lang}-friendly references. Family's primary language is {lang}.",
                    strength=0.7,
                    graph_path=[cultural.id],
                    metadata={"language": lang},
                ))

        return results

    async def _enrich_with_llm(self, implications: list[CoachingImplication]) -> list[CoachingImplication]:
        summaries = "\n".join(f"- {i.implication}" for i in implications[:5])
        prompt = (
            "Based on these socioeconomic signals, provide ONE additional synthesized coaching insight (1 sentence):\n"
            f"{summaries}\n\nInsight:"
        )
        try:
            synthesis = await self._llm.complete(prompt, temperature=0.3)
            if synthesis.strip():
                implications.append(CoachingImplication(
                    category="synthesis",
                    implication=synthesis.strip(),
                    strength=0.6,
                    metadata={"source": "llm_synthesis"},
                ))
        except Exception as exc:
            logger.debug("LLM synthesis error: %s", exc)
        return implications
