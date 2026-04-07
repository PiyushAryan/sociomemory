from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from sociomemory.models.coaching import IncomeEstimate


class SocioProfile(BaseModel):
    """
    A computed VIEW over the MemoryGraph. Not stored — derived on demand.
    Think of it as a SQL VIEW: derived, not persisted.
    """

    child_id: str

    # Location
    area_type: str = "unknown"  # "urban_affluent", "urban_middle", "semi_urban", "rural"
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    # Connectivity
    connectivity_score: float = 0.5

    # Resources nearby
    resource_availability: dict[str, int] = Field(default_factory=dict)
    # e.g. {"therapy_centers": 3, "parks": 5, "hospitals": 2}

    # Safety
    safety_profile: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"aqi_avg": 120, "child_safety_score": 0.7, "overall": 0.65}

    # Culture
    cultural_context: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"primary_language": "Kannada", "cosmopolitan": 0.8}

    # Economy
    economic_tier: str = "unknown"
    income_estimate: Optional[IncomeEstimate] = None
    real_estate_context: dict[str, Any] = Field(default_factory=dict)

    # School
    school_context: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"name": "DPS", "board": "CBSE", "fee_tier": "high"}

    # Family
    family_context: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"parent_profession": "IT", "employer": "Infosys"}

    # Behavioral / identity
    lifestyle_tags: list[str] = Field(default_factory=list)
    religious_context: Optional[dict[str, Any]] = None
    visit_summary: dict[str, int] = Field(default_factory=dict)
    # e.g. {"temple": 3, "park": 8, "mountain": 1}

    # Meta
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_enriched: datetime = Field(default_factory=datetime.utcnow)
    graph_stats: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"nodes": 142, "edges": 287, "gaps": ["school", "profession"]}

    def to_llm_context(self, include_sensitive: bool = False) -> str:
        """Serialize to natural language for LLM system prompt injection."""
        lines: list[str] = [f"## Social Context for child {self.child_id}"]

        if self.city:
            lines.append(f"- Location: {self.neighborhood or ''}, {self.city}, {self.state or ''}")
        if self.area_type != "unknown":
            lines.append(f"- Area type: {self.area_type}")
        if self.income_estimate:
            ie = self.income_estimate
            lines.append(
                f"- Income bracket: {ie.bracket} (₹{ie.monthly_range[0]:,}–{ie.monthly_range[1]:,}/mo, "
                f"confidence {ie.confidence:.0%})"
            )
        if self.school_context:
            sc = self.school_context
            lines.append(
                f"- School: {sc.get('name', 'unknown')} ({sc.get('board', '')},"
                f" {sc.get('medium', '')} medium, fee tier: {sc.get('fee_tier', '')})"
            )
        if self.family_context:
            fc = self.family_context
            if fc.get("employer"):
                lines.append(f"- Parent employer: {fc['employer']} ({fc.get('industry', '')})")
        if self.cultural_context:
            lang = self.cultural_context.get("primary_language")
            if lang:
                lines.append(f"- Primary language: {lang}")
        if self.lifestyle_tags:
            lines.append(f"- Lifestyle: {', '.join(self.lifestyle_tags)}")
        if self.religious_context:
            lines.append(f"- Religious context: {self.religious_context.get('tradition', 'unknown')}")
        if self.resource_availability:
            tc = self.resource_availability.get("therapy_centers", 0)
            if tc:
                lines.append(f"- Nearby therapy centers: {tc}")
        if self.safety_profile:
            aqi = self.safety_profile.get("aqi_avg")
            if aqi:
                lines.append(f"- AQI: {aqi} ({'poor' if aqi > 150 else 'moderate' if aqi > 100 else 'good'})")

        if not include_sensitive:
            lines.append("_(sensitive data omitted)_")

        return "\n".join(lines)
