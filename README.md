# sociomemory

**Graph memory engine for social context inference — built for VIRa AI Coach**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1)
![FAISS](https://img.shields.io/badge/FAISS-in--process-orange)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Patent](https://img.shields.io/badge/patent-pending-orange)

> **⚠️ PROPRIETARY SOFTWARE — NOT FREE TO USE.**
> sociomemory is a closed, source-available proprietary library owned by **NirvanaAIsutra Technologies Pvt. Ltd.** It is **not** open source and is **not** licensed for personal, academic, research, evaluation, internal-business, or commercial use without a signed Commercial Agreement. Possession of this package — including via PyPI, GitHub, or any mirror — grants no rights of use. One or more inventions embodied herein are **patent pending**. See [`LICENSE`](LICENSE) for full terms. To license, contact **licensing@nirvanaaisutra.com**.

---

## What is sociomemory?

Children with neurodevelopmental disorders (ASD, ADHD, Dyslexia) don't arrive in a vacuum. They arrive from Koramangala or Dharavi, from CBSE schools or Anganwadis, from Infosys households or daily-wage families. An AI coach that ignores this context gives generic advice. sociomemory makes sure VIRa never does.

sociomemory is a **standalone, pip-installable Python library** that builds a living graph of social, economic, and cultural context around a child — inferred from sparse conversation signals. When a child says "I live in Koramangala", the library does not store a string. It traverses a knowledge graph and arrives at: upper-middle income family, IT hub neighbourhood, Kannada-speaking, outdoor parks within 2 km, Cubbon Park nearby, can afford professional OT therapy.

The core idea is simple: **every piece of knowledge is a node, every relationship is an edge, every inference is a traversal. The graph IS the memory.**

sociomemory is India-first. It ships with bundled data for Indian cities, neighbourhoods, real-estate tiers, school boards, and cultural regions — so it works offline, out of the box, without any API calls.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         sociomemory                             │
│                                                                 │
│   Conversation text                                             │
│        │                                                        │
│        ▼                                                        │
│   ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│   │  Extractor   │───▶│   Enricher   │───▶│   Implicator    │   │
│   │  (signals)   │    │  (providers) │    │  (coaching)     │   │
│   └──────────────┘    └──────┬───────┘    └────────┬────────┘   │
│                              │                     │            │
│              ┌───────────────┼─────────────────────┘            │
│              ▼               ▼                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                   MemoryGraph                          │    │
│   │                                                        │    │
│   │   Neo4j (brain)        FAISS (vector search)           │    │
│   │   ┌──────────────┐     ┌────────────────────┐          │    │
│   │   │ Nodes/Edges  │     │  Embeddings index  │          │    │
│   │   │ LIVES_IN     │     │  per child         │          │    │
│   │   │ DERIVES      │     └────────────────────┘          │    │
│   │   │ UPDATES      │                                     │    │
│   │   │ IMPLIES      │     SQLite (cache + consent)        │    │
│   │   └──────────────┘     ┌────────────────────┐          │    │
│   │                        │  enrichment cache  │          │    │
│   └────────────────────────│  consent records   │─────────┘     │
│                            └────────────────────┘               │
│                                                                 │
│   Engines                  Providers                            │
│   ┌───────────────────┐    ┌───────────────────────────────┐    │
│   │ IncomeEstimator   │    │ OfflineLocationProvider       │    │
│   │ BehavioralInf.    │    │   bundled india_cities.json   │    │
│   │ TradeOffDetector  │    │   india_real_estate.json      │    │
│   │ VersioningEngine  │    │   cultural_regions.json       │    │
│   └───────────────────┘    │ ExaLocationProvider (online)  │    │
│                            └───────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## How it works — the inference chain

A single sentence from a session triggers a multi-hop graph traversal:

```
Child: "We live in Koramangala"
         │
         ▼
[SignalExtractor]  →  Signal(type=LOCATION, value="Koramangala", confidence=0.85)
         │
         ▼
[OfflineLocationProvider]  →  reads india_cities.json + india_real_estate.json
         │
         ├──▶  Node(NEIGHBORHOOD, name="Koramangala", area_type="urban_affluent")
         ├──▶  Node(CITY, name="Bengaluru")
         ├──▶  Node(REAL_ESTATE, avg_rent_2bhk=55000, area_type="premium")
         ├──▶  Node(CULTURAL, primary_language="Kannada", cosmopolitan=0.85)
         ├──▶  Node(ECONOMIC, income_tier="upper_middle")
         ├──▶  Node(TRANSPORT, metro_access=True, connectivity_score=0.82)
         └──▶  Node(SAFETY, aqi_avg=95, child_safety_score=0.74)
                        │
                        ▼
          [IncomeEstimator — multi-hop convergence]
                        │
          Path 1: RealEstate.avg_rent=55000 → bracket=upper_middle (weight 0.35)
          Path 2: School.fee_yearly         → bracket=upper_middle (weight 0.25)  ← if known
          Path 3: Employer.industry         → bracket=upper_middle (weight 0.25)  ← if known
          Path 4: Economic.income_tier=upper_middle        (weight 0.15)
                        │
                        ▼
          IncomeEstimate(bracket="upper_middle",
                         monthly_range=(100000, 250000),
                         confidence=0.78,
                         affordability_index=0.78)
                        │
                        ▼
          [CoachingImplicator]
          → "Family can afford private OT therapy (₹2000–4000/session)"
          → "Cubbon Park 2.1 km away — viable for outdoor sensory walks"
          → "IT background: high digital literacy, app-based exercises will land well"
```

Every inferred node stores:
- `confidence` — how certain we are
- `source_chunk` — the exact verbatim sentence that triggered it
- `document_date` — when we captured it
- `event_date` — when it actually happened (for temporal queries)
- `sensitivity` — PUBLIC / CONTEXTUAL / PERSONAL / SENSITIVE

---

## Behavioral place intelligence

Visit patterns build identity without asking directly.

| Child mentions visiting… | sociomemory infers… |
|---|---|
| ISKCON temple regularly | `religious=krishna_devotee`, `dietary=vegetarian_likely`, therapy narrative: Krishna stories |
| Temple (generic) | `religious=hindu` |
| Mosque | `religious=muslim`, `dietary=halal_likely` |
| Gurudwara | `religious=sikh`, `dietary=vegetarian_likely` |
| Hill station / trekking | `lifestyle=outdoor_active`, `sensory=cold_tolerant` |
| Beach / water park | `lifestyle=outdoor_active`, `sensory=water_comfortable` → aqua therapy candidate |
| Mall (frequent) | `lifestyle=urban_explorer`, `sensory=crowd_tolerant` → group therapy viable |
| Museum / zoo / science centre | `lifestyle=experiential_learner` → museum-based learning sessions |
| Library | `lifestyle=quiet_preference` → low-stimulation session environment preferred |

Therapy opportunities are surfaced automatically from these patterns — e.g. confirmed water comfort becomes an aqua therapy recommendation with a confidence score attached.

---

## Quick start

### Install

```bash
# Core (offline-capable)
pip install sociomemory

# With Exa.ai online enrichment
pip install "sociomemory[online]"
```

### Connect to Neo4j AuraDB Free

```python
import asyncio
from sociomemory import Sociomemory, SociomemoryConfig

config = SociomemoryConfig(
    neo4j_uri="neo4j+s://xxxxxxxx.databases.neo4j.io",  # AuraDB free tier
    neo4j_user="neo4j",
    neo4j_password="your-aura-password",
    llm_backend="gemini",
    llm_api_key="your-gemini-api-key",
    exa_api_key="your-exa-key",          # optional — enables online enrichment
)

async def main():
    async with Sociomemory(config) as sm:
        # Ingest a conversation turn
        result = await sm.ingest(
            child_id="child_001",
            text="We live in Koramangala. My son goes to DPS, Bangalore.",
        )
        print(result)
        # {'status': 'ok', 'signals': 2, 'nodes_added': 9, 'edges_added': 7}

        # Get structured profile
        profile = await sm.get_profile("child_001")
        print(profile.income_estimate.bracket)               # 'upper_middle'
        print(profile.income_estimate.affordability_index)   # 0.78

        # Get LLM-ready context string
        context = await sm.get_context_for_llm("child_001")
        print(context)

asyncio.run(main())
```

### Ingest a structured signal directly

```python
async with Sociomemory(config) as sm:
    await sm.ingest_signal(
        child_id="child_001",
        signal_type="visit",
        value="iskcon",
        confidence=0.9,
    )

    # Ask a natural language question against the graph
    answer = await sm.query("child_001", "What therapy approaches suit this family?")
```

### Refresh stale nodes

When a fact changes (family moves neighbourhoods), downstream derived nodes are cascade-staled and need recomputation:

```python
async with Sociomemory(config) as sm:
    report = await sm.refresh("child_001")
    print(report)  # {'stale_nodes': 4, 'node_ids': [...]}
```

---

## Configuration reference

`SociomemoryConfig` is a plain Python dataclass — no environment variables required (though `.env` files work via `python-dotenv`).

```python
from sociomemory import SociomemoryConfig
from pathlib import Path

config = SociomemoryConfig(
    # Neo4j — local or AuraDB
    neo4j_uri="bolt://localhost:7687",       # AuraDB: "neo4j+s://xxxx.databases.neo4j.io"
    neo4j_user="neo4j",
    neo4j_password="password",
    neo4j_database="neo4j",                  # AuraDB always uses "neo4j"

    # LLM backend
    llm_backend="gemini",                    # "gemini" | "openai" | "ollama"
    llm_api_key="...",
    llm_model="",                            # leave empty for per-backend default

    # Local storage (FAISS + SQLite)
    data_dir=Path.home() / ".sociomemory",   # auto-created; FAISS + SQLite live here

    # Behaviour
    offline_only=False,                      # True = never call any external API
    country="IN",                            # India-first defaults
    embedding_dim=768,                       # must match your LLM's embedding output

    # Online enrichment
    exa_api_key="",                          # leave empty to use offline-only mode
    enrichment_cache_ttl_hours=24,           # how long to cache Exa responses (hours)
)
```

---

## Providers

sociomemory resolves location and school signals through a provider chain. Offline runs first; online augments.

### Offline (bundled, zero dependencies)

Bundled JSON files in `sociomemory/data/`:

| File | Contents |
|---|---|
| `india_cities.json` | ~500 cities with coordinates, state, tier classification |
| `india_real_estate.json` | Neighbourhood-level rent bands, area type, premium score |
| `cultural_regions.json` | Language, religion, cuisine, cosmopolitan index by city/region |
| `school_boards.json` | CBSE / ICSE / State board profiles, typical fee bands, medium |
| `amenity_categories.json` | Amenity type → behavioural category mappings |

Offline providers cover the vast majority of Indian urban and semi-urban contexts without any network call.

### Exa.ai (online enrichment)

Install `sociomemory[online]` and set `exa_api_key` to enable real-time enrichment:

- Civic and political context for the neighbourhood
- Current therapy centres and special-needs schools nearby
- Local community resources, NGOs, and support groups
- Recent safety and infrastructure updates

Exa results are LLM-parsed and stored in the graph with a TTL (default 24 hours). All Exa calls are cached in SQLite — repeated ingestion of the same location does not re-hit the API.

---

## Privacy and consent

sociomemory stores sensitive inferences about real children. Privacy is a first-class concern, not an afterthought.

### Node sensitivity levels

Every node carries a `DataLevel`:

| Level | Examples | Default behaviour |
|---|---|---|
| `PUBLIC` | City, state, area type | Always available |
| `CONTEXTUAL` | Neighbourhood, school board, income bracket | Available with basic consent |
| `PERSONAL` | School name, employer, exact address | Requires explicit consent scope |
| `SENSITIVE` | Religious identity, dietary inferences | Requires explicit consent scope |

### Consent API

```python
from sociomemory import Sociomemory, ConsentScope

async with Sociomemory(config) as sm:
    # Record parental consent (SQLite-backed, per child per scope)
    sm.privacy.record_consent(
        child_id="child_001",
        parent_id="parent_A",
        scope=ConsentScope.INCOME_INFERENCE,
        granted=True,
    )
    sm.privacy.record_consent(
        child_id="child_001",
        parent_id="parent_A",
        scope=ConsentScope.RELIGIOUS_CONTEXT,
        granted=False,       # parent opts out
    )

    # Check before using
    if sm.privacy.check_consent("child_001", ConsentScope.RELIGIOUS_CONTEXT):
        # use religious context in prompt
        pass
```

Available `ConsentScope` values: `LOCATION_AREA`, `LOCATION_EXACT`, `INCOME_INFERENCE`, `SCHOOL_DATA`, `RELIGIOUS_CONTEXT`, `BEHAVIORAL_PROFILING`, `EMPLOYER_DATA`, `EXPORT`.

### GDPR erasure

```python
async with Sociomemory(config) as sm:
    # Deletes all Neo4j nodes/edges, FAISS index, and consent records for the child
    await sm.privacy.erase("child_001")
```

---

## VIRa integration

sociomemory plugs into VIRa at four points.

### 1. System prompt enrichment

Inject social context into every LLM call so VIRa always knows the family's world:

```python
async with Sociomemory(config) as sm:
    context_block = await sm.get_context_for_llm("child_001")

system_prompt = f"""
You are VIRa, an AI coach for children with neurodevelopmental disorders.

{context_block}

Use this context to personalise every response. Suggest activities that are
geographically accessible, culturally appropriate, and within family budget.
"""
```

The context block looks like:

```
## Socioeconomic Context (Graph-Derived)
- Income: upper_middle (₹1,00,000–₹2,50,000/mo, confidence 78%)
- Area: Koramangala (urban_affluent)
- AQI: 95 (good)
- Primary language: Kannada
- Lifestyle: outdoor_active, urban_explorer
- Religious: krishna_devotee (72%)
- Therapy opportunities: adventure therapy, cultural narrative, group therapy
```

### 2. Signal ingestion from session turns

Feed every conversation turn through sociomemory to continuously build the graph:

```python
async def on_child_message(child_id: str, text: str, sm: Sociomemory):
    result = await sm.ingest(child_id, text)
    if result.get("signals", 0) > 0:
        # Graph updated — next LLM call will have richer context
        pass
```

### 3. Activity selection

Use the structured profile to filter and rank activities:

```python
async with Sociomemory(config) as sm:
    profile = await sm.get_profile("child_001")
    income = profile.income_estimate

    # Filter to affordable activities
    affordable = [
        activity for activity in activity_library
        if activity.cost_tier <= income.affordability_index
    ]

    # Boost outdoor activities if lifestyle matches
    if "outdoor_active" in profile.lifestyle_tags:
        outdoor = [a for a in affordable if a.category == "outdoor"]
        # prioritise these in the recommendation set
```

### 4. ChildProfile construction

Build a complete `ChildProfile` for VIRa's domain model:

```python
async with Sociomemory(config) as sm:
    profile = await sm.get_profile("child_001")

child_profile = ChildProfile(
    id="child_001",
    city=profile.city,
    neighbourhood=profile.neighborhood,
    income_bracket=profile.economic_tier,
    affordability_index=profile.income_estimate.affordability_index if profile.income_estimate else 0.5,
    school_board=profile.school_context.get("board"),
    primary_language=profile.cultural_context.get("primary_language"),
    lifestyle_tags=profile.lifestyle_tags,
    nearby_therapy_centers=profile.resource_availability.get("therapy_centers", 0),
    graph_confidence=profile.confidence,
)
```

---

## Relational versioning

sociomemory tracks how facts change over time using three edge types:

| Edge | Meaning | Effect |
|---|---|---|
| `UPDATES` | New fact replaces old (family moved) | Old node kept for history; downstream `DERIVES` nodes cascade-staled |
| `EXTENDS` | New fact adds detail without contradiction | Confidence increases; no staling |
| `DERIVES` | Node was computed by combining other nodes | Automatically re-queued when dependencies stale |

When a family moves from Koramangala to Whitefield, call `VersioningEngine.update_node(old_hood_id, new_hood_node)` and all income estimates, transport scores, and therapy implications derived from the old neighbourhood are automatically marked stale. `sm.refresh("child_001")` returns the stale node IDs in topological recomputation order.

### Dual-layer timestamps

Every node carries two timestamps:

- `document_date` — when sociomemory captured this fact (wall-clock time of ingest)
- `event_date` — when the event actually happened (e.g. a visit last summer)

This enables temporal queries like "What was the family's income estimate last year?" or "Did they visit a hill station in summer 2025?"

---

## Development setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker (for local Neo4j)

### Install

```bash
git clone https://github.com/nirvana-ai/sociomemory
cd sociomemory

# Install with dev dependencies
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

### Run Neo4j locally with Docker

```bash
docker run \
  --name sociomemory-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/testpassword \
  neo4j:5
```

Connect with:

```python
config = SociomemoryConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="testpassword",
    llm_backend="ollama",   # no API key needed for local dev
)
```

### Run tests

```bash
uv run pytest

# With coverage
uv run pytest --cov=sociomemory
```

Tests use `testcontainers` to spin up an ephemeral Neo4j instance — no manual Docker setup needed beyond having Docker running.

### Lint and format

```bash
uv run ruff check sociomemory/
uv run ruff format sociomemory/
```

---

## Module reference

```
sociomemory/
├── __init__.py          Sociomemory  (public API class)
├── config.py            SociomemoryConfig  (dataclass)
├── graph/
│   ├── nodes.py         Node, NodeType, DataLevel
│   ├── edges.py         Edge, EdgeType  (UPDATES/EXTENDS/DERIVES + structural)
│   ├── memory_graph.py  MemoryGraph  (per-child graph interface)
│   ├── reasoner.py      GraphReasoner  (income, behavioral, gaps, context string)
│   ├── builder.py       GraphBuilder  (subgraph construction helpers)
│   ├── cypher.py        Cypher query constants
│   └── schema.py        Neo4j index / constraint definitions
├── engine/
│   ├── income.py        IncomeEstimator  (multi-hop convergence, 4 signal paths)
│   ├── behavioral.py    BehavioralInference  (visit pattern → identity)
│   ├── tradeoff.py      TradeOffDetector
│   ├── temporal.py      TemporalEngine  (event_date queries)
│   ├── versioning.py    VersioningEngine  (UPDATES/EXTENDS/cascade staling)
│   └── scorer.py        ConfidenceScorer
├── pipeline/
│   ├── extractor.py     SignalExtractor  (regex + LLM fallback)
│   ├── enricher.py      EnrichmentPipeline  (signals → graph nodes)
│   └── implicator.py    CoachingImplicator  (graph → actionable coaching)
├── providers/
│   ├── offline.py       OfflineLocationProvider, OfflineSchoolProvider
│   └── exa.py           ExaLocationProvider  (requires [online])
├── storage/
│   ├── neo4j_backend.py Neo4jBackend  (async driver wrapper)
│   ├── vector.py        FaissIndex  (per-child in-process FAISS index)
│   └── cache.py         SQLiteCache  (enrichment result cache + TTL)
├── llm/
│   ├── base.py          BaseLLM  (protocol)
│   ├── gemini.py        GeminiLLM
│   ├── openai.py        OpenAILLM
│   └── local.py         OllamaLLM
├── privacy/
│   ├── consent.py       ConsentManager, ConsentScope
│   ├── boundaries.py    SensitivityFilter
│   └── anonymizer.py    Anonymizer
└── data/
    ├── india_cities.json
    ├── india_real_estate.json
    ├── cultural_regions.json
    ├── school_boards.json
    └── amenity_categories.json
```

---

## License

**Proprietary — All Rights Reserved.** See [LICENSE](LICENSE) for the full Sociomemory Proprietary Software License Agreement.

This software is **not** open source and is **not** free to use. No rights of use, copy, modification, redistribution, hosting, fine-tuning, benchmarking, or derivative work are granted by default — including for personal, academic, research, evaluation, internal-business, or commercial purposes. Use is permitted **only** under a separate signed Commercial Agreement executed with NirvanaAIsutra Technologies Pvt. Ltd.

**Patent Pending.** One or more inventions embodied in this software — including methods for inferring socioeconomic and cultural context from sparse conversational signals via a graph memory engine, multi-hop inferential traversal, cascade-versioned memory, and privacy-scoped consent boundaries — are the subject of pending patent applications. No patent license is granted.

**Bundled datasets** (`india_cities.json`, `india_real_estate.json`, `cultural_regions.json`, `school_boards.json`, `amenity_categories.json`) are proprietary curated compilations protected as database/compilation works. Extraction or re-use of any substantial part is expressly prohibited.

For commercial, evaluation, or academic licensing inquiries: **licensing@nirvanaaisutra.com**

Built by **NirvanaAIsutra** for VIRa, an AI Agentic Coach for children with ASD, ADHD, and Dyslexia. India-first.
