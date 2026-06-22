from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

from sociomemory.graph.nodes import NodeType
from sociomemory.models.coaching import IncomeEstimate

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph

logger = logging.getLogger(__name__)

BRACKETS: dict[str, tuple[int, int]] = {
    "low": (0, 25_000),
    "lower_middle": (25_000, 50_000),
    "middle": (50_000, 100_000),
    "upper_middle": (100_000, 250_000),
    "high": (250_000, 1_000_000),
}

AFFORDABILITY = {
    "low": 0.1,
    "lower_middle": 0.3,
    "middle": 0.55,
    "upper_middle": 0.78,
    "high": 0.95,
}

IT_TIER1 = {
    "infosys",
    "tcs",
    "wipro",
    "accenture",
    "ibm",
    "cognizant",
    "microsoft",
    "google",
    "amazon",
    "meta",
    "flipkart",
}


def _bracket_from_monthly(monthly: float) -> str:
    for name, (lo, hi) in BRACKETS.items():
        if lo <= monthly < hi:
            return name
    return "high" if monthly >= 250_000 else "low"


class IncomeEstimator:
    def __init__(self, graph: MemoryGraph):
        self._graph = graph

    async def estimate(self) -> IncomeEstimate | None:
        signals: list[tuple[str, str, float]] = []

        re_nodes = await self._graph.get_nodes_by_type(NodeType.REAL_ESTATE)
        for re in re_nodes:
            rent = re.properties.get("avg_rent_2bhk")
            if rent and rent > 0:
                signals.append(("location_rent", _bracket_from_monthly(rent / 0.275), 0.35))
                break

        school_nodes = await self._graph.get_nodes_by_type(NodeType.SCHOOL)
        for school in school_nodes:
            fee = school.properties.get("fee_yearly")
            if fee and fee > 0:
                signals.append(("school_fee", _bracket_from_monthly((fee / 0.12) / 12), 0.25))
                break

        employer_nodes = await self._graph.get_nodes_by_type(NodeType.EMPLOYER)
        for emp in employer_nodes:
            bracket = self._employer_bracket(emp.properties)
            if bracket:
                signals.append(("employer_industry", bracket, 0.25))
                break

        econ_nodes = await self._graph.get_nodes_by_type(NodeType.ECONOMIC)
        for econ in econ_nodes:
            tier = econ.properties.get("income_tier", "").lower()
            if tier in BRACKETS:
                signals.append(("area_economic", tier, 0.15))
                break

        if not signals:
            return None

        brackets = [s[1] for s in signals]
        source_names = [s[0] for s in signals]
        majority = Counter(brackets).most_common(1)[0][0]
        agreement = brackets.count(majority) / len(brackets)
        confidence = min(0.95, 0.3 + 0.4 * agreement + 0.1 * len(signals))

        lo, hi = BRACKETS[majority]
        return IncomeEstimate(
            bracket=majority,
            monthly_range=(lo, hi),
            confidence=round(confidence, 3),
            convergence_score=round(agreement, 3),
            signals_used=source_names,
            affordability_index=AFFORDABILITY.get(majority, 0.5),
        )

    def _employer_bracket(self, props: dict) -> str | None:
        industry = (props.get("industry") or "").lower()
        name = (props.get("name") or "").lower()
        for n in IT_TIER1:
            if n in name:
                return "upper_middle"
        if any(k in industry for k in ("it", "software", "tech")):
            return "middle"
        if any(k in industry for k in ("bank", "finance", "insurance")):
            return "upper_middle"
        if any(k in industry for k in ("government", "psu", "railway")):
            return "middle"
        return None
