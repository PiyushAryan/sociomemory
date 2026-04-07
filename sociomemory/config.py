from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SociomemoryConfig:
    # --- Neo4j ---
    neo4j_uri: str = "bolt://localhost:7687"   # AuraDB: "neo4j+s://xxxx.databases.neo4j.io"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"             # AuraDB always uses "neo4j"

    # --- LLM backend ---
    llm_backend: str = "gemini"          # "gemini" | "openai" | "local"
    llm_api_key: str = ""
    llm_model: str = ""                  # default per backend if empty

    # --- FAISS + SQLite ---
    data_dir: Path = field(default_factory=lambda: Path.home() / ".sociomemory")

    # --- Behaviour ---
    offline_only: bool = False           # never call external APIs
    country: str = "IN"                  # India-first defaults
    embedding_dim: int = 768             # must match LLM embedder

    # --- Enrichment ---
    google_maps_api_key: str = ""
    exa_api_key: str = ""
    enrichment_cache_ttl_hours: int = 24

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "faiss").mkdir(exist_ok=True)

    @property
    def faiss_dir(self) -> Path:
        return self.data_dir / "faiss"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "cache.db"
