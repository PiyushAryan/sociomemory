from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class OpenAILLM:
    """OpenAI backend."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", embed_model: str = "text-embedding-3-small"):
        self._api_key = api_key
        self._model = model
        self._embed_model = embed_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai is required: pip install openai")
        return self._client

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await client.chat.completions.create(
                model=self._model, messages=messages, temperature=temperature
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.error("OpenAI completion error: %s", exc)
            return ""

    async def embed(self, text: str) -> list[float]:
        client = self._get_client()
        try:
            resp = await client.embeddings.create(model=self._embed_model, input=text)
            return resp.data[0].embedding
        except Exception as exc:
            logger.error("OpenAI embed error: %s", exc)
            return []

    async def health_check(self) -> bool:
        try:
            result = await self.complete("ping", temperature=0.0)
            return bool(result)
        except Exception:
            return False
