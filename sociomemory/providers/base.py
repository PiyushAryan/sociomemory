from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sociomemory.graph.edges import Edge
from sociomemory.graph.nodes import Node
from sociomemory.models.signals import Signal

if TYPE_CHECKING:
    from sociomemory.graph.memory_graph import MemoryGraph


@runtime_checkable
class BaseProvider(Protocol):
    provider_name: str
    requires_network: bool

    async def enrich(self, signal: Signal, graph: MemoryGraph) -> tuple[list[Node], list[Edge]]: ...

    async def health_check(self) -> bool: ...
