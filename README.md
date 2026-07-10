# sociomemory

[![PyPI](https://img.shields.io/pypi/v/sociomemory.svg)](https://pypi.org/project/sociomemory/)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

`sociomemory` is a Python package for building a graph of social, economic, cultural,
location, education, work, and behavioral context around a subject profile. It is
designed for agent applications that need structured context instead of one flat memory
string.

The package is India-first: it ships with bundled offline reference data for Indian
cities, neighborhoods, real estate bands, school boards, cultural regions, and amenity
categories. Optional online and LLM providers can enrich that data when configured.

## What it does

- Extracts or accepts structured signals such as location, education, profession,
  visits, language, housing, and lifestyle.
- Enriches signals through offline providers and configured online providers.
- Stores context as a graph with typed nodes, edges, confidence, timestamps, and data
  sensitivity levels.
- Produces structured profiles and LLM-ready context blocks.
- Includes privacy controls for consent, filtering, export, and erasure.
- Supports Neo4j by default, with a backend protocol for other graph stores.

This is infrastructure for context-aware applications.

## Installation

```bash
pip install sociomemory
```

The standard install includes runtime libraries for graph storage, vector recall,
LLM adapters, Exa enrichment, spaCy-assisted NER, and geo helpers. No runtime
extras are required.

## Requirements

- Python 3.11+
- Neo4j 5.x, unless you provide a custom `GraphBackend`
- API keys for hosted LLM or online enrichment providers when those features are enabled

For a local Neo4j instance:

```bash
docker run \
  --name sociomemory-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/testpassword \
  neo4j:5
```

## Quick Start

This example uses direct structured signals, so it works without an LLM API key.

Note: the current API uses `child_id` as the profile identifier parameter name for
backward compatibility. You can pass any stable subject or profile id.

```python
import asyncio

from sociomemory import Sociomemory, SociomemoryConfig


config = SociomemoryConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="testpassword",
    llm_backend="none",
    offline_only=True,
)


async def main():
    profile_id = "profile_001"

    async with Sociomemory(config) as sm:
        await sm.ingest_signal(
            child_id=profile_id,
            signal_type="location",
            value="Koramangala",
            confidence=0.9,
        )

        await sm.ingest_signal(
            child_id=profile_id,
            signal_type="school",
            value="DPS Bangalore",
            confidence=0.8,
        )

        profile = await sm.get_profile(profile_id)
        print(profile.city)
        print(profile.neighborhood)
        print(profile.economic_tier)

        context = await sm.get_context_for_llm(profile_id)
        print(context)


asyncio.run(main())
```

## Conversation Ingestion

With an LLM backend configured, `ingest()` can extract signals from free text.

```python
import asyncio

from sociomemory import Sociomemory, SociomemoryConfig


config = SociomemoryConfig(
    neo4j_uri="neo4j+s://your-db.databases.neo4j.io",
    neo4j_user="neo4j",
    neo4j_password="your-password",
    llm_backend="gemini",
    llm_api_key="your-gemini-key",
)


async def main():
    profile_id = "profile_001"

    async with Sociomemory(config) as sm:
        result = await sm.ingest(
            child_id=profile_id,
            text="We live in Koramangala and use the metro to commute.",
        )
        print(result)


asyncio.run(main())
```

Supported LLM backends are `gemini`, `openai`, `openrouter`, `ollama`, `local`, and
`none`.

## Configuration

`SociomemoryConfig` is a plain dataclass:

```python
from pathlib import Path

from sociomemory import SociomemoryConfig


config = SociomemoryConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
    neo4j_database="neo4j",
    llm_backend="openrouter",
    llm_api_key="sk-or-...",
    llm_model="",
    llm_embedding_model="",
    data_dir=Path.home() / ".sociomemory",
    offline_only=False,
    enforce_consent=True,
    country="IN",
    embedding_dim=768,
    exa_api_key="",
    enrichment_cache_ttl_hours=24,
)
```

## Privacy

Each graph node carries a sensitivity level. When `enforce_consent=True`,
`sociomemory` checks consent before sensitive operations.

```python
from sociomemory import ConsentScope, Sociomemory


async def privacy_example(config):
    profile_id = "profile_001"

    async with Sociomemory(config) as sm:
        sm.privacy.record_consent(
            child_id=profile_id,
            parent_id="owner_001",
            scope=ConsentScope.LOCATION_AREA,
            granted=True,
        )

        sm.privacy.record_consent(
            child_id=profile_id,
            parent_id="owner_001",
            scope=ConsentScope.RELIGIOUS_CONTEXT,
            granted=False,
        )

        sm.privacy.record_consent(
            child_id=profile_id,
            parent_id="owner_001",
            scope=ConsentScope.EXPORT,
            granted=True,
        )

        exported = await sm.privacy.export_data(profile_id)
        await sm.privacy.erase(profile_id)
        return exported
```

Consent scopes include:

- `LOCATION_AREA`
- `LOCATION_EXACT`
- `INCOME_INFERENCE`
- `SCHOOL_DATA`
- `RELIGIOUS_CONTEXT`
- `BEHAVIORAL_PROFILING`
- `EMPLOYER_DATA`
- `EXPORT`

## Custom Graph Backends

Neo4j is the default storage adapter. To use another graph database, implement the
`GraphBackend` protocol and inject it:

```python
from sociomemory import Sociomemory, SociomemoryConfig


backend = MyGraphBackend(...)
memory = Sociomemory(
    SociomemoryConfig(llm_backend="none"),
    graph_backend=backend,
)
```

The graph domain layer uses semantic backend operations; database-specific queries and
transactions stay inside the adapter.

## Development

```bash
git clone https://github.com/piyusharyan/sociomemory
cd sociomemory

uv sync --extra dev
uv run pytest -m "not integration and not network"
uv run ruff check .
uv run ruff format --check .
uv run mypy sociomemory
uv run python -m build
```

Integration tests that touch Neo4j require Docker.

## License

MIT. See [LICENSE](LICENSE).
