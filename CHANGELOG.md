# Changelog

All notable changes to `sociomemory` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `NodeType.CIVIC` as an allowed target of `NEIGHBORHOOD --HAS_CONTEXT-->` in the graph schema.
- `ECONOMIC --DERIVES--> INCOME` edge in the graph schema.

## [0.1.0] - 2026-05-16

Initial alpha release of the graph memory engine for social context inference.

### Added
- `MemoryGraph` engine with Neo4j-backed graph storage and FAISS vector index.
- Signal extraction, enrichment, and coaching-implication pipeline
  (`SignalExtractor`, `EnrichmentPipeline`, `CoachingImplicator`).
- Domain models: `SocioProfile`, `IncomeEstimate`, `CoachingImplication`, `TradeOff`.
- Privacy layer: `ConsentManager`, `ConsentScope`, GDPR-style erase/export APIs.
- LLM provider abstractions for Gemini, OpenAI, and local backends.
- Online/offline data providers (Exa optional via `online` extra).
- India-focused reference data: cities, real-estate tiers, school boards, cultural regions, amenity categories.
- Optional extras: `online` (Exa), `geo` (geopandas/shapely), `dev` (pytest, ruff, testcontainers).
