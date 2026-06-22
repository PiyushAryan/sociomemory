from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_EMBED_MODEL = "text-embedding-3-small"  # 1536-dim


class OpenAILLM:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        embed_model: str = DEFAULT_OPENAI_EMBED_MODEL,
    ):
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

    async def web_search(self, query: str, model: str | None = None) -> str:
        client = self._get_client()
        try:
            resp = await client.responses.create(
                model=model or self._model,
                tools=[{"type": "web_search"}],
                input=query,
            )
            return resp.output_text or ""
        except Exception as exc:
            logger.error("OpenAI web_search error: %s", exc)
            return ""

    async def health_check(self) -> bool:
        try:
            result = await self.complete("ping", temperature=0.0)
            return bool(result)
        except Exception:
            return False
