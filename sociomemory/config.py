from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SociomemoryConfig:
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = ""
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    llm_backend: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_embedding_model: str = ""

    data_dir: Path = field(default_factory=lambda: Path.home() / ".sociomemory")

    offline_only: bool = False
    enforce_consent: bool = False
    country: str = "IN"
    embedding_dim: int = 768

    exa_api_key: str = ""
    enrichment_cache_ttl_hours: int = 24

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.llm_backend = self.llm_backend.lower()
        allowed_backends = {"gemini", "openai", "openrouter", "ollama", "local", "none"}
        if self.llm_backend not in allowed_backends:
            raise ValueError(f"Unsupported llm_backend: {self.llm_backend}")
        if self.embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive")
        if self.enrichment_cache_ttl_hours <= 0:
            raise ValueError("enrichment_cache_ttl_hours must be positive")
        if len(self.country) != 2 or not self.country.isalpha():
            raise ValueError("country must be a two-letter country code")
        self.country = self.country.upper()

    @property
    def faiss_dir(self) -> Path:
        return self.data_dir / "faiss"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "cache.db"
