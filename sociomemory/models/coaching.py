from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class IncomeEstimate(BaseModel):
    bracket: str  # "low", "lower_middle", "middle", "upper_middle", "high"
    monthly_range: tuple[int, int]
    confidence: float = Field(ge=0.0, le=1.0)
    convergence_score: float = Field(ge=0.0, le=1.0)
    signals_used: list[str] = Field(default_factory=list)
    affordability_index: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def monthly_midpoint(self) -> int:
        return (self.monthly_range[0] + self.monthly_range[1]) // 2

    def can_afford(self, monthly_cost: int, threshold: float = 0.15) -> bool:
        return monthly_cost <= self.monthly_midpoint * threshold


class CoachingImplication(BaseModel):
    category: str  # "activity", "tone", "resource", "goal", "therapy"
    implication: str
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    graph_path: list[str] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradeOff(BaseModel):
    dimension: str
    positive_node_id: str
    negative_node_id: str
    positive_summary: str
    negative_summary: str
    tension_score: float = Field(default=0.5, ge=0.0, le=1.0)
    resolution: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
