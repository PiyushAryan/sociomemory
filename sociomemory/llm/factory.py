from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sociomemory.config import SociomemoryConfig
    from sociomemory.llm.base import BaseLLM


def build_llm(config: SociomemoryConfig) -> BaseLLM | None:
    backend = config.llm_backend
    key = config.llm_api_key
    kwargs = {"api_key": key}
    if config.llm_model:
        kwargs["model"] = config.llm_model
    if config.llm_embedding_model:
        kwargs["embed_model"] = config.llm_embedding_model

    if backend == "gemini" and key:
        from sociomemory.llm.gemini import GeminiLLM

        return GeminiLLM(**kwargs)
    if backend == "openai" and key:
        from sociomemory.llm.openai import OpenAILLM

        return OpenAILLM(**kwargs)
    if backend == "openrouter" and key:
        from sociomemory.llm.openrouter import OpenRouterLLM

        return OpenRouterLLM(**kwargs)
    if backend in {"local", "ollama"}:
        from sociomemory.llm.local import OllamaLLM

        return OllamaLLM()
    return None
