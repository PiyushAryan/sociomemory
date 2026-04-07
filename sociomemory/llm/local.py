from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OllamaLLM:
    """Ollama local model backend."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        embed_model: str = "nomic-embed-text",
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._embed_model = embed_model

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "")
        except Exception as exc:
            logger.error("Ollama completion error: %s", exc)
            return ""

    async def embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._embed_model, "prompt": text},
                )
                resp.raise_for_status()
                return resp.json().get("embedding", [])
        except Exception as exc:
            logger.error("Ollama embed error: %s", exc)
            return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
