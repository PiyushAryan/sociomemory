# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

Uses `uv` (see `uv.lock`) but `pip -e` also works. Python 3.11+, line length 100.

```bash
# Install dev environment
uv sync --extra dev            # or: pip install -e ".[dev]"

# Full test suite (asyncio_mode=auto, strict-markers enabled)
uv run pytest
uv run pytest tests/test_income.py::test_name   # single test
uv run pytest -m "not integration and not network"  # what CI runs
uv run pytest --cov=sociomemory --cov-fail-under=45  # CI coverage gate

# Lint / format / typecheck (all three run in CI)
uv run ruff check .
uv run ruff format --check .   # CI uses --check; drop it to auto-format
uv run mypy sociomemory

# Build wheel + sdist
uv run python -m build

# Local Neo4j for integration tests / dev
docker run --name sociomemory-neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/testpassword neo4j:5

# Dashboard (source-checkout only — excluded from the wheel)
./sociomemory/dashboard/dev.sh
```

Pytest markers `integration` and `network` are declared in `pyproject.toml`; CI skips both. Integration tests spin up Neo4j via `testcontainers` (in the `dev` extra) — Docker must be running.

Env vars honored by the dashboard and by scripts sourcing `.env.local`: `SOCIOMEMORY_NEO4J_*`, `SOCIOMEMORY_LLM_BACKEND`, `SOCIOMEMORY_LLM_API_KEY`, `SOCIOMEMORY_LLM_MODEL`, `SOCIOMEMORY_LLM_EMBEDDING_MODEL`, `SOCIOMEMORY_EMBEDDING_DIM`, `SOCIOMEMORY_EXA_API_KEY`, `SOCIOMEMORY_DATA_DIR`, `SOCIOMEMORY_OFFLINE_ONLY`, `SOCIOMEMORY_COUNTRY`.

## Architecture

sociomemory is a pip-installable Python library that ingests conversation text and builds a per-child social/economic/cultural knowledge graph. The core mental model: **every fact is a node, every relationship is an edge, every inference is a graph traversal. The graph IS the memory.** `docs/architecture.md` has full mermaid diagrams — read it before making structural changes.

### Request flow (one ingest call touches all layers)

`Sociomemory.ingest(child_id, text)` in `sociomemory/__init__.py` is the facade. A single call chains:

1. **`pipeline/extractor.py` — SignalExtractor**: regex patterns first, LLM fallback second, returns typed `Signal` objects.
2. **Consent gate**: `Sociomemory._SIGNAL_CONSENT` maps `SignalType → ConsentScope`. When `config.enforce_consent=True`, missing consent raises before any provider or graph write.
3. **`providers/factory.py` — build_providers**: builds a provider chain per signal type. Offline providers (bundled JSON in `sociomemory/data/`) always run; `providers/exa.py` layers on when `exa_api_key` is set and `offline_only=False`.
4. **`pipeline/enricher.py` — EnrichmentPipeline**: providers return `(nodes, edges)`; the pipeline hands them to `GraphBuilder` and then merges into `MemoryGraph`.
5. **`graph/memory_graph.py` — MemoryGraph**: per-child, holds a reference to the shared `GraphBackend` plus a per-child FAISS index and BM25 index. Cached in `Sociomemory._graphs` dict — instantiated lazily.
6. **`storage/neo4j_backend.py` — Neo4jBackend**: async driver wrapper implementing the `GraphBackend` protocol. All Cypher lives in `graph/cypher.py`; the backend translates domain nodes/edges to parameters and back.

### The GraphBackend protocol (pluggable graph DB)

`sociomemory/storage/graph_backend.py` is the port. `Neo4jBackend` is the default adapter, but callers can inject any implementation:

```python
Sociomemory(config, graph_backend=MyMemgraphBackend(...))
```

`MemoryGraph`, `GraphReasoner`, `VersioningEngine`, and the privacy layer only use semantic protocol methods (`merge_subgraph`, `traverse`, `find_inference_chains`, `mark_stale`, etc.) — they must not import Neo4j-specific types. If you add a method to the protocol, update `Neo4jBackend` and any tests that mock the backend.

### Triple storage — what lives where

- **Neo4j** — the graph itself (28 node types, 20 edge types), scoped by `child_id` on every node and edge.
- **FAISS** (`storage/vector.py`) — per-child in-process vector index at `data_dir/faiss/{child_id}.faiss`. If `faiss-cpu` isn't installed, `NullVectorIndex` is used so the library still works.
- **BM25** (`storage/keyword.py`) — per-child lexical index at `data_dir/keyword/`.
- **SQLite** — two separate DB files: `cache.db` (Exa enrichment cache with TTL) and `cache_consent.db` (parent consent records). Never used for graph storage.

`config.data_dir` (default `~/.sociomemory`) owns all four. `privacy.erase(child_id)` must clean up all four for GDPR compliance.

### Inference engines vs profile as a computed view

`SocioProfile` (`models/profile.py`) is **never persisted** — it's built on every `get_profile()` call by `GraphReasoner` running fresh graph queries. If you find yourself caching the profile, stop: freshness/consistency is the invariant.

Inference engines in `sociomemory/engine/` each do one thing:
- `income.py` — 4-path convergence (rent, school fee, employer industry, area tier) with weighted majority + confidence formula.
- `behavioral.py` — visit patterns → religious/dietary/lifestyle/sensory identity nodes with logarithmic confidence growth.
- `versioning.py` — `UPDATES` supersedes and cascade-stales downstream `DERIVES` nodes; `EXTENDS` adds detail without staling; `recompute_stale()` returns node IDs in topological order for the caller to re-derive.
- `temporal.py` / `episodes.py` — use the dual timestamps.
- `tradeoff.py`, `scorer.py` — contradiction detection, node ranking.

### Two timestamps on every node

- `document_date` — when sociomemory captured the fact (wall-clock at ingest).
- `event_date` — when the event actually happened, extracted from context.

Never conflate them. Freshness decay uses `document_date`; queries like "what happened last summer" use `event_date`. `sociomemory/time.py` provides `utc_now()` — use it, don't call `datetime.now()` directly.

### Privacy — enforced at multiple layers

- **DataLevel** on each node (`PUBLIC`/`CONTEXTUAL`/`PERSONAL`/`SENSITIVE`) — `privacy/boundaries.py` filters by max level.
- **ConsentScope** per child (`privacy/consent.py`) — checked at ingest (via `_require_signal_consent`) and at read time (`get_profile` gates income/behavior/religion/location/school/employer sections). `enforce_consent` defaults to `False` for back-compat; test with it both on and off.
- **Anonymizer** (`privacy/anonymizer.py`) — pseudonymizes PII in source chunks before export.
- **Erasure** (`privacy/api.py`) — must delete from Neo4j, FAISS, BM25, and the consent DB atomically.

### LLM abstraction

`llm/factory.py` routes `config.llm_backend` to `gemini` / `openai` / `openrouter` / `ollama` (aka `local`) / `none`. All backends implement `BaseLLM` (`llm/base.py`) with `complete()` and `embed()`. The `none` backend disables LLM fallback in the extractor and skips embedding writes — code paths must handle `self._llm is None`.

### India-first data assumptions

Bundled JSON in `sociomemory/data/` (cities, real-estate tiers, cultural regions, school boards, amenity categories) is India-specific. `config.country` defaults to `"IN"`. Extending to other countries means new data files plus provider changes — don't hardcode country logic in the graph or engine layers.

### What's excluded from the wheel

`pyproject.toml` `[tool.hatch.build.targets.wheel]` excludes `sociomemory/tests`, `sociomemory/dashboard`, and `__pycache__`. The dashboard is a dev-only artifact; if you add code it depends on into the library, keep imports lazy so import-time doesn't pull dashboard deps.
