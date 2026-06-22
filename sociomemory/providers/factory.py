from __future__ import annotations

from typing import TYPE_CHECKING

from sociomemory.models.signals import SignalType
from sociomemory.providers.offline import (
    OfflineLocationProvider,
    OfflineSchoolProvider,
    OfflineVisitProvider,
)

if TYPE_CHECKING:
    from sociomemory.config import SociomemoryConfig
    from sociomemory.llm.base import BaseLLM
    from sociomemory.providers.base import BaseProvider
    from sociomemory.storage.cache import SQLiteCache


def build_providers(
    signal_type: SignalType,
    config: SociomemoryConfig,
    llm: BaseLLM | None,
    cache: SQLiteCache,
) -> list[BaseProvider]:
    if signal_type == SignalType.LOCATION:
        providers: list[BaseProvider] = [OfflineLocationProvider()]
        if not config.offline_only and config.exa_api_key and llm:
            from sociomemory.providers.exa import ExaLocationProvider

            providers.append(
                ExaLocationProvider(
                    config.exa_api_key,
                    llm,
                    cache,
                    config.enrichment_cache_ttl_hours,
                )
            )
        return providers

    if signal_type == SignalType.SCHOOL:
        return [OfflineSchoolProvider()]

    if signal_type == SignalType.VISIT:
        providers = [OfflineVisitProvider()]
        if not config.offline_only and llm:
            from sociomemory.providers.place import PlaceEnrichmentProvider

            providers.append(
                PlaceEnrichmentProvider(
                    llm,
                    cache,
                    config.exa_api_key,
                    config.enrichment_cache_ttl_hours,
                )
            )
        return providers

    return []
