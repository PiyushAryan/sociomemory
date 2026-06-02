from __future__ import annotations

import sys
import types

from sociomemory import Sociomemory, SociomemoryConfig
from sociomemory.llm.openrouter import (
    DEFAULT_OPENROUTER_EMBED_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterLLM,
)


def test_openrouter_client_uses_openai_compatible_base_url(monkeypatch):
    calls = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))

    llm = OpenRouterLLM(
        api_key="sk-or-test",
        model=DEFAULT_OPENROUTER_MODEL,
        embed_model=DEFAULT_OPENROUTER_EMBED_MODEL,
        app_url="https://nirvanaaisutra.com",
        app_title="sociomemory",
    )
    llm._get_client()

    assert calls["api_key"] == "sk-or-test"
    assert calls["base_url"] == "https://openrouter.ai/api/v1"
    assert calls["default_headers"] == {
        "HTTP-Referer": "https://nirvanaaisutra.com",
        "X-OpenRouter-Title": "sociomemory",
    }


def test_sociomemory_builds_openrouter_backend_from_config(tmp_path):
    config = SociomemoryConfig(
        llm_backend="openrouter",
        llm_api_key="sk-or-test",
        data_dir=tmp_path,
    )
    memory = Sociomemory(config)

    llm = memory._build_llm()

    assert isinstance(llm, OpenRouterLLM)
    assert llm._model == DEFAULT_OPENROUTER_MODEL
    assert llm._embed_model == DEFAULT_OPENROUTER_EMBED_MODEL
