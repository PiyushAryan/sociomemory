from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BaseLLM(Protocol):

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.2) -> str: ...

    async def embed(self, text: str) -> list[float]: ...

    async def health_check(self) -> bool: ...
