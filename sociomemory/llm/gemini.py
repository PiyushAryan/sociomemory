from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class GeminiLLM:
    def __init__(
        self, api_key: str, model: str = "gemini-2.0-flash", embed_model: str = "text-embedding-004"
    ):
        self._api_key = api_key
        self._model = model
        self._embed_model = embed_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                raise ImportError("google-genai is required: pip install google-genai")
        return self._client

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        client = self._get_client()
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        try:
            response = client.models.generate_content(model=self._model, contents=full_prompt)
            return response.text or ""
        except Exception as exc:
            logger.error("Gemini completion error: %s", exc)
            return ""

    async def embed(self, text: str) -> list[float]:
        client = self._get_client()
        try:
            response = client.models.embed_content(model=self._embed_model, contents=text)
            return response.embeddings[0].values
        except Exception as exc:
            logger.error("Gemini embed error: %s", exc)
            return []

    async def health_check(self) -> bool:
        try:
            result = await self.complete("ping", temperature=0.0)
            return bool(result)
        except Exception:
            return False
