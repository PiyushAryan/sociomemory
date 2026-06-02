from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_OPENROUTER_MODEL = "moonshotai/kimi-k2.6:free"
DEFAULT_OPENROUTER_EMBED_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"


class OpenRouterLLM:

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENROUTER_MODEL,
        embed_model: str = DEFAULT_OPENROUTER_EMBED_MODEL,
        base_url: str = "https://openrouter.ai/api/v1",
        app_url: str = "",
        app_title: str = "sociomemory",
    ):
        self._api_key = api_key
        self._model = model
        self._embed_model = embed_model
        self._base_url = base_url.rstrip("/")
        self._app_url = app_url or os.getenv("SOCIOMEMORY_OPENROUTER_APP_URL", "")
        self._app_title = app_title or os.getenv("SOCIOMEMORY_OPENROUTER_APP_TITLE", "sociomemory")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("openai is required for OpenRouter: pip install openai")

            headers = {}
            if self._app_url:
                headers["HTTP-Referer"] = self._app_url
            if self._app_title:
                headers["X-OpenRouter-Title"] = self._app_title
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                default_headers=headers or None,
            )
        return self._client

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.error("OpenRouter completion error: %s", exc)
            return ""

    async def embed(self, text: str) -> list[float]:
        client = self._get_client()
        try:
            resp = await client.embeddings.create(model=self._embed_model, input=text)
            return resp.data[0].embedding
        except Exception as exc:
            logger.error("OpenRouter embed error: %s", exc)
            return []

    async def health_check(self) -> bool:
        try:
            result = await self.complete("ping", temperature=0.0)
            return bool(result)
        except Exception:
            return False
