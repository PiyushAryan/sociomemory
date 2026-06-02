from __future__ import annotations

import logging
import math
from collections import Counter
from typing import TYPE_CHECKING

from sociomemory.graph.nodes import NodeType

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph

logger = logging.getLogger(__name__)


def _confidence(count: int) -> float:
    return min(0.95, 0.3 + 0.3 * math.log1p(count))


class BehavioralInference:

    def __init__(self, graph: "MemoryGraph"):
        self._graph = graph

    async def infer_identity(self) -> dict:
        visits = await self._graph.get_nodes_by_type(NodeType.VISIT)
        religious: Counter = Counter()
        lifestyle: Counter = Counter()
        sensory: Counter = Counter()
        dietary: Counter = Counter()

        for visit in visits:
            pt = (visit.properties.get("place_type") or "").lower()
            ps = (visit.properties.get("place_subtype") or "").lower()

            if pt == "temple":
                if "iskcon" in ps:
                    religious["krishna_devotee"] += 1
                    dietary["vegetarian_likely"] += 1
                else:
                    religious["hindu"] += 1
            elif pt == "mosque":
                religious["muslim"] += 1
                dietary["halal_likely"] += 1
            elif pt == "church":
                religious["christian"] += 1
            elif pt == "gurudwara":
                religious["sikh"] += 1
                dietary["vegetarian_likely"] += 1

            if pt in ("mountain", "hill_station", "trekking"):
                lifestyle["outdoor_active"] += 1
                sensory["cold_tolerant"] += 1
            elif pt in ("beach", "water_park"):
                lifestyle["outdoor_active"] += 1
                sensory["water_comfortable"] += 1
            elif pt in ("park", "playground"):
                lifestyle["outdoor_active"] += 1
            elif pt == "mall":
                lifestyle["urban_explorer"] += 1
                sensory["crowd_tolerant"] += 1
            elif pt in ("museum", "zoo", "science_center"):
                lifestyle["experiential_learner"] += 1
            elif pt == "library":
                lifestyle["quiet_preference"] += 1

        result: dict = {}
        if religious:
            top = religious.most_common(1)[0]
            result["religious"] = {"identity": top[0], "confidence": _confidence(top[1]), "visits": top[1]}
        if lifestyle:
            result["lifestyle"] = {tag: {"confidence": _confidence(c), "visits": c} for tag, c in lifestyle.most_common(3)}
        if sensory:
            result["sensory"] = {sig: {"confidence": _confidence(c), "visits": c} for sig, c in sensory.most_common()}
        if dietary:
            top = dietary.most_common(1)[0]
            result["dietary"] = {"tag": top[0], "confidence": _confidence(top[1])}
        return result

    async def suggest_therapy_opportunities(self) -> list[dict]:
        identity = await self.infer_identity()
        opportunities = []
        lifestyle = identity.get("lifestyle", {})
        sensory = identity.get("sensory", {})
        religious = identity.get("religious", {})

        if lifestyle.get("outdoor_active", {}).get("confidence", 0) > 0.5:
            opportunities.append({
                "type": "adventure_therapy",
                "rationale": "Family is outdoor-active",
                "confidence": lifestyle["outdoor_active"]["confidence"],
            })
        if sensory.get("water_comfortable", {}).get("confidence", 0) > 0.5:
            opportunities.append({
                "type": "aqua_therapy",
                "rationale": "Water comfort confirmed from visits",
                "confidence": sensory["water_comfortable"]["confidence"],
            })
        if sensory.get("crowd_tolerant", {}).get("confidence", 0) > 0.4:
            opportunities.append({
                "type": "group_therapy",
                "rationale": "Crowd tolerance suggests group settings are viable",
                "confidence": sensory["crowd_tolerant"]["confidence"],
            })
        if religious.get("identity") in ("krishna_devotee", "hindu"):
            opportunities.append({
                "type": "cultural_narrative",
                "rationale": "Use Krishna/Hindu stories as therapy narrative bridges",
                "confidence": religious["confidence"],
            })
        if lifestyle.get("experiential_learner", {}).get("confidence", 0) > 0.4:
            opportunities.append({
                "type": "museum_based_learning",
                "rationale": "Family invests in experiential learning trips",
                "confidence": lifestyle["experiential_learner"]["confidence"],
            })
        return opportunities
