# Changelog

All notable changes to `sociomemory` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-08

### Added
- `NodeType.CIVIC` as an allowed target of `NEIGHBORHOOD --HAS_CONTEXT-->` in the graph schema.
- `ECONOMIC --DERIVES--> INCOME` edge in the graph schema.
- BM25 keyword recall with persistent per-child indexes and FAISS-free fallback behavior.
- Optional fail-closed consent enforcement and consent-gated full data exports.
- Python 3.11/3.12 CI for linting, tests, coverage, and wheel installation.

### Changed
- Split LLM/provider construction and privacy operations out of the public client module.
- Moved provider SDKs, FAISS, and geospatial dependencies into explicit package extras.
- Normalized model timestamps to timezone-aware UTC values.
- Consolidated tests under the top-level `tests/` directory.
- Removed decorative and implementation-narrating comments from the Python sources.

### Fixed
- Prevented child identifiers from escaping local index directories.
- Erasure now evicts in-memory indexes and removes BM25 data in addition to FAISS data.
- Dynamic Cypher relationship names and traversal depths are validated before interpolation.
- `enrichment_cache_ttl_hours` is now honored by online providers.

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
