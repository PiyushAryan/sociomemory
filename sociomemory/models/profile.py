from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from sociomemory.models.coaching import IncomeEstimate
from sociomemory.time import ensure_utc, utc_now


class SocioProfile(BaseModel):
    child_id: str
    area_type: str = "unknown"
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    connectivity_score: float = 0.5
    resource_availability: dict[str, int] = Field(default_factory=dict)
    safety_profile: dict[str, Any] = Field(default_factory=dict)
    cultural_context: dict[str, Any] = Field(default_factory=dict)
    economic_tier: str = "unknown"
    income_estimate: IncomeEstimate | None = None
    real_estate_context: dict[str, Any] = Field(default_factory=dict)
    school_context: dict[str, Any] = Field(default_factory=dict)
    family_context: dict[str, Any] = Field(default_factory=dict)
    lifestyle_tags: list[str] = Field(default_factory=list)
    religious_context: dict[str, Any] | None = None
    visit_summary: dict[str, int] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_enriched: datetime = Field(default_factory=utc_now)
    graph_stats: dict[str, Any] = Field(default_factory=dict)

    _normalize_datetimes = field_validator("last_enriched")(ensure_utc)

    def to_llm_context(self, include_sensitive: bool = False) -> str:
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
            lines.append(
                f"- Religious context: {self.religious_context.get('tradition', 'unknown')}"
            )
        if self.resource_availability:
            tc = self.resource_availability.get("therapy_centers", 0)
            if tc:
                lines.append(f"- Nearby therapy centers: {tc}")
        if self.safety_profile:
            aqi = self.safety_profile.get("aqi_avg")
            if aqi:
                lines.append(
                    f"- AQI: {aqi} ({'poor' if aqi > 150 else 'moderate' if aqi > 100 else 'good'})"
                )

        if not include_sensitive:
            lines.append("_(sensitive data omitted)_")

        return "\n".join(lines)
