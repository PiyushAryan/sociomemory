from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from sociomemory.config import SociomemoryConfig
from sociomemory.graph.memory_graph import MemoryGraph
from sociomemory.graph.nodes import NodeType
from sociomemory.graph.reasoner import GraphReasoner
from sociomemory.llm.factory import build_llm
from sociomemory.models.coaching import CoachingImplication, IncomeEstimate, TradeOff
from sociomemory.models.profile import SocioProfile
from sociomemory.models.signals import SignalSource, SignalType
from sociomemory.pipeline.enricher import EnrichmentPipeline
from sociomemory.pipeline.extractor import SignalExtractor
from sociomemory.pipeline.implicator import CoachingImplicator
from sociomemory.privacy.api import PrivacyAPI
from sociomemory.privacy.consent import ConsentManager, ConsentScope
from sociomemory.providers.factory import build_providers
from sociomemory.storage.cache import SQLiteCache
from sociomemory.storage.graph_backend import GraphBackend
from sociomemory.storage.keyword import BM25Index
from sociomemory.storage.vector import FaissIndex, NullVectorIndex, VectorIndex

try:
    __version__ = version("sociomemory")
except PackageNotFoundError:
    __version__ = "0.1.0"
__all__ = [
    "Sociomemory",
    "SociomemoryConfig",
    "SocioProfile",
    "IncomeEstimate",
    "CoachingImplication",
    "TradeOff",
    "ConsentScope",
    "GraphBackend",
]


class Sociomemory:
    _SIGNAL_CONSENT = {
        SignalType.LOCATION: ConsentScope.LOCATION_AREA,
        SignalType.SCHOOL: ConsentScope.SCHOOL_DATA,
        SignalType.PARENT_PROFESSION: ConsentScope.EMPLOYER_DATA,
        SignalType.VISIT: ConsentScope.BEHAVIORAL_PROFILING,
        SignalType.RELIGIOUS: ConsentScope.RELIGIOUS_CONTEXT,
        SignalType.INCOME: ConsentScope.INCOME_INFERENCE,
        SignalType.HOUSING: ConsentScope.INCOME_INFERENCE,
        SignalType.DIETARY: ConsentScope.RELIGIOUS_CONTEXT,
        SignalType.LANGUAGE: ConsentScope.BEHAVIORAL_PROFILING,
        SignalType.TRANSPORT: ConsentScope.BEHAVIORAL_PROFILING,
        SignalType.FAMILY_STRUCTURE: ConsentScope.BEHAVIORAL_PROFILING,
        SignalType.SENSORY: ConsentScope.BEHAVIORAL_PROFILING,
        SignalType.LIFESTYLE: ConsentScope.BEHAVIORAL_PROFILING,
        SignalType.GENERIC: ConsentScope.BEHAVIORAL_PROFILING,
    }

    def __init__(
        self,
        config: SociomemoryConfig,
        graph_backend: GraphBackend | None = None,
    ):
        self._config = config
        if graph_backend is None:
            from sociomemory.storage.neo4j_backend import Neo4jBackend

            graph_backend = Neo4jBackend(
                config.neo4j_uri,
                config.neo4j_user,
                config.neo4j_password,
                config.neo4j_database,
            )
        self._backend = graph_backend
        self._cache = SQLiteCache(str(config.sqlite_path))
        self._consent = ConsentManager(str(config.sqlite_path).replace(".db", "_consent.db"))
        self._graphs: dict[str, MemoryGraph] = {}
        self._llm = None
        self.privacy = PrivacyAPI(
            consent=self._consent,
            backend=self._backend,
            graphs=self._graphs,
            faiss_dir=config.faiss_dir,
            keyword_dir=config.data_dir / "keyword",
        )

    async def connect(self) -> None:
        await self._backend.connect()
        await self._backend.init_schema()
        self._llm = self._build_llm()

    async def close(self) -> None:
        await self._backend.close()
        self._cache.close()
        self._consent.close()

    async def __aenter__(self) -> Sociomemory:
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    def _build_llm(self):
        return build_llm(self._config)

    def _get_graph(self, child_id: str) -> MemoryGraph:
        if child_id not in self._graphs:
            faiss: VectorIndex
            try:
                faiss = FaissIndex(
                    child_id=child_id,
                    dim=self._config.embedding_dim,
                    data_dir=str(self._config.faiss_dir),
                )
            except ImportError:
                faiss = NullVectorIndex()
            keyword = BM25Index(
                child_id=child_id,
                data_dir=str(self._config.data_dir / "keyword"),
            )
            self._graphs[child_id] = MemoryGraph(
                child_id=child_id,
                backend=self._backend,
                faiss=faiss,
                keyword=keyword,
                embedder=self._llm,
            )
        return self._graphs[child_id]

    def _build_providers(self, signal_type) -> list:
        return build_providers(signal_type, self._config, self._llm, self._cache)

    def _require_signal_consent(self, child_id: str, signal_type: SignalType) -> None:
        if not self._config.enforce_consent:
            return
        scope = self._SIGNAL_CONSENT.get(signal_type)
        if scope:
            self.privacy.require_consent(child_id, scope)

    async def ensure_child_node(self, child_id: str, name: str | None = None) -> str:
        graph = self._get_graph(child_id)
        child_nodes = await graph.get_nodes_by_type(NodeType.CHILD)
        if child_nodes:
            node = child_nodes[0]
            if name and node.properties.get("name") != name:
                await graph.update_node_properties(node.id, NodeType.CHILD, {"name": name})
            return node.id
        properties = {"child_id": child_id}
        if name:
            properties["name"] = name
        child_node = await graph.add_node(
            node_type=NodeType.CHILD,
            properties=properties,
            confidence=1.0,
        )
        return child_node.id

    async def ingest_person(
        self,
        child_id: str,
        *,
        name: str | None = None,
        area: str | None = None,
        school: str | None = None,
        places: list[str] | None = None,
        notes: str | None = None,
    ) -> dict:
        await self.ensure_child_node(child_id, name=name)
        steps: dict[str, Any] = {}
        if area and area.strip():
            steps["area"] = await self.ingest_signal(child_id, "location", area.strip())
        if school and school.strip():
            steps["school"] = await self.ingest_signal(child_id, "school", school.strip())
        for place in places or []:
            place = (place or "").strip()
            if place:
                steps[f"visit:{place}"] = await self.ingest(
                    child_id, f"We recently visited {place}."
                )
        if notes and notes.strip():
            steps["notes"] = await self.ingest(child_id, notes.strip())
        summary = await (await self.get_graph(child_id)).summary()
        return {"child_id": child_id, "name": name, "steps": steps, "summary": summary}

    async def ingest(self, child_id: str, text: str, source: str = "conversation") -> dict:
        warnings = []
        if self._llm is None:
            warnings.append(
                "LLM is not configured; free-text extraction is limited to explicit offline "
                "visit keywords. Configure an LLM backend for full entity extraction."
            )
        extractor = SignalExtractor(llm=self._llm)
        source_enum = (
            SignalSource(source)
            if source in SignalSource._value2member_map_
            else SignalSource.CONVERSATION
        )
        signals = await extractor.extract(text, source=source_enum)

        if not signals:
            result = {"status": "no_signals"}
            if warnings:
                result["warnings"] = warnings
            return result

        for signal in signals:
            self._require_signal_consent(child_id, signal.signal_type)
        await self.ensure_child_node(child_id)
        graph = self._get_graph(child_id)
        providers_map = {sig.signal_type: self._build_providers(sig.signal_type) for sig in signals}
        pipeline = EnrichmentPipeline(graph=graph, providers=providers_map)
        result = await pipeline.enrich(signals)
        result["signals"] = len(signals)
        if warnings:
            result["warnings"] = warnings
        return result

    async def ingest_signal(
        self, child_id: str, signal_type: str, value: str, confidence: float = 1.0
    ) -> dict:
        from sociomemory.models.signals import Signal

        sig = Signal(
            raw_text=value,
            signal_type=SignalType(signal_type),
            extracted_value=value,
            confidence=confidence,
            source=SignalSource.PROFILE,
        )
        self._require_signal_consent(child_id, sig.signal_type)
        await self.ensure_child_node(child_id)
        graph = self._get_graph(child_id)
        providers = self._build_providers(sig.signal_type)
        pipeline = EnrichmentPipeline(graph=graph, providers={sig.signal_type: providers})
        return await pipeline.enrich([sig])

    async def acquire_location(
        self,
        child_id: str,
        lat: float,
        lng: float,
        accuracy_m: float | None = None,
    ) -> dict:
        if not -90 <= lat <= 90:
            raise ValueError("lat must be between -90 and 90")
        if not -180 <= lng <= 180:
            raise ValueError("lng must be between -180 and 180")
        if self._config.enforce_consent:
            self.privacy.require_consent(child_id, ConsentScope.LOCATION_EXACT)

        await self.ensure_child_node(child_id)
        location_match = self._resolve_location(lat, lng)
        h3_index = self._h3_index(lat, lng)
        acquired_value = location_match.label if location_match else f"{lat:.5f},{lng:.5f}"

        from sociomemory.models.signals import Signal

        metadata = {
            "accuracy_m": accuracy_m,
            "acquired_via": "browser_geolocation",
            "location_resolved": bool(location_match),
            "resolution_source": location_match.source if location_match else None,
            "nearest_distance_km": location_match.distance_km if location_match else None,
            "h3_cells": h3_index.cells if h3_index else {},
            "h3_source": h3_index.source if h3_index else None,
        }
        sig = Signal(
            raw_text=f"Browser geolocation acquired near {acquired_value}.",
            signal_type=SignalType.LOCATION,
            extracted_value=acquired_value,
            confidence=0.82 if location_match else 0.55,
            source=SignalSource.PROFILE,
            metadata=metadata,
        )
        graph = self._get_graph(child_id)
        providers = self._build_providers(SignalType.LOCATION)
        pipeline = EnrichmentPipeline(graph=graph, providers={SignalType.LOCATION: providers})
        result = await pipeline.enrich([sig])
        result["location"] = acquired_value
        result["location_resolved"] = bool(location_match)
        result["resolution_source"] = location_match.source if location_match else None
        result["nearest_distance_km"] = location_match.distance_km if location_match else None
        result["h3_cells"] = h3_index.cells if h3_index else {}
        result["online_enrichment"] = any(
            getattr(provider, "requires_network", False) for provider in providers
        )
        return result

    def _resolve_location(self, lat: float, lng: float):
        from sociomemory.providers.geocode import OfflineGeoResolver

        return OfflineGeoResolver().reverse(lat, lng)

    def _h3_index(self, lat: float, lng: float):
        from sociomemory.providers.geocode import h3_cell_index

        return h3_cell_index(lat, lng)

    async def get_graph(self, child_id: str) -> MemoryGraph:
        await self.ensure_child_node(child_id)
        return self._get_graph(child_id)

    async def list_children(self, limit: int = 100) -> list[str]:
        return await self._backend.list_children(limit=limit)

    async def get_profile(self, child_id: str) -> SocioProfile:
        graph = self._get_graph(child_id)
        reasoner = GraphReasoner(graph=graph, llm=self._llm)
        allow_income = not self._config.enforce_consent or self.privacy.check_consent(
            child_id, ConsentScope.INCOME_INFERENCE
        )
        allow_behavior = not self._config.enforce_consent or self.privacy.check_consent(
            child_id, ConsentScope.BEHAVIORAL_PROFILING
        )
        allow_religion = not self._config.enforce_consent or self.privacy.check_consent(
            child_id, ConsentScope.RELIGIOUS_CONTEXT
        )
        allow_location = not self._config.enforce_consent or self.privacy.check_consent(
            child_id, ConsentScope.LOCATION_AREA
        )
        allow_school = not self._config.enforce_consent or self.privacy.check_consent(
            child_id, ConsentScope.SCHOOL_DATA
        )
        allow_employer = not self._config.enforce_consent or self.privacy.check_consent(
            child_id, ConsentScope.EMPLOYER_DATA
        )
        income = await reasoner.infer_income() if allow_income else None
        identity = await reasoner.get_behavioral_identity() if allow_behavior else {}
        if not allow_religion:
            identity.pop("religious", None)

        hood_nodes = await graph.get_nodes_by_type(NodeType.NEIGHBORHOOD)
        city_nodes = await graph.get_nodes_by_type(NodeType.CITY)
        safety_nodes = await graph.get_nodes_by_type(NodeType.SAFETY)
        cultural_nodes = await graph.get_nodes_by_type(NodeType.CULTURAL)
        school_nodes = await graph.get_nodes_by_type(NodeType.SCHOOL)
        employer_nodes = await graph.get_nodes_by_type(NodeType.EMPLOYER)
        transport_nodes = await graph.get_nodes_by_type(NodeType.TRANSPORT)
        econ_nodes = await graph.get_nodes_by_type(NodeType.ECONOMIC)
        re_nodes = await graph.get_nodes_by_type(NodeType.REAL_ESTATE)

        if not allow_location:
            hood_nodes = []
            city_nodes = []
            safety_nodes = []
            cultural_nodes = []
            transport_nodes = []
            econ_nodes = []
            re_nodes = []
        if not allow_school:
            school_nodes = []
        if not allow_employer:
            employer_nodes = []

        stats = await graph.summary()
        gaps = await reasoner.identify_gaps()

        return SocioProfile(
            child_id=child_id,
            area_type=econ_nodes[0].properties.get("area_type", "unknown")
            if econ_nodes
            else "unknown",
            neighborhood=hood_nodes[0].properties.get("name") if hood_nodes else None,
            city=city_nodes[0].properties.get("name") if city_nodes else None,
            safety_profile=safety_nodes[0].properties if safety_nodes else {},
            cultural_context=cultural_nodes[0].properties if cultural_nodes else {},
            school_context=school_nodes[0].properties if school_nodes else {},
            family_context=employer_nodes[0].properties if employer_nodes else {},
            connectivity_score=transport_nodes[0].properties.get("connectivity_score", 0.5)
            if transport_nodes
            else 0.5,
            real_estate_context=re_nodes[0].properties if re_nodes else {},
            income_estimate=income,
            economic_tier=income.bracket if income else "unknown",
            lifestyle_tags=list(identity.get("lifestyle", {}).keys()),
            religious_context=identity.get("religious"),
            graph_stats={**stats, "gaps": gaps},
        )

    async def get_income_estimate(self, child_id: str) -> IncomeEstimate | None:
        if self._config.enforce_consent:
            self.privacy.require_consent(child_id, ConsentScope.INCOME_INFERENCE)
        graph = self._get_graph(child_id)
        return await GraphReasoner(graph=graph, llm=self._llm).infer_income()

    async def get_coaching_implications(self, child_id: str) -> list[CoachingImplication]:
        graph = self._get_graph(child_id)
        return await CoachingImplicator(graph=graph, llm=self._llm).generate()

    async def get_tradeoffs(self, child_id: str) -> list[TradeOff]:
        graph = self._get_graph(child_id)
        return await GraphReasoner(graph=graph, llm=self._llm).detect_tradeoffs()

    async def query(self, child_id: str, question: str) -> str:
        if self._config.enforce_consent:
            context = await self.get_context_for_llm(child_id)
            if self._llm:
                return await self._llm.complete(
                    f"Approved context:\n{context}\n\nQuestion: {question}\nAnswer:",
                    temperature=0.2,
                )
            return context
        graph = self._get_graph(child_id)
        if self._llm:
            embedding = await self._llm.embed(question)
            if embedding:
                import numpy as np

                subgraph = await graph.extract_context_subgraph(
                    np.array(embedding), query_text=question
                )
                if subgraph.nodes:
                    context = "\n".join(
                        f"- {n.type.value}: {n.properties}" for n in subgraph.nodes[:10]
                    )
                    return await self._llm.complete(
                        f"Graph context:\n{context}\n\nQuestion: {question}\nAnswer:",
                        temperature=0.2,
                    )
        subgraph = await graph.extract_context_subgraph(query_text=question)
        if subgraph.nodes and self._llm:
            context = "\n".join(f"- {n.type.value}: {n.properties}" for n in subgraph.nodes[:10])
            return await self._llm.complete(
                f"Graph context:\n{context}\n\nQuestion: {question}\nAnswer:", temperature=0.2
            )
        return await GraphReasoner(graph=graph, llm=self._llm).generate_coaching_context()

    async def get_context_for_llm(self, child_id: str) -> str:
        if self._config.enforce_consent:
            profile = await self.get_profile(child_id)
            return profile.to_llm_context(include_sensitive=False)
        graph = self._get_graph(child_id)
        return await GraphReasoner(graph=graph, llm=self._llm).generate_coaching_context()

    async def identify_gaps(self, child_id: str) -> list[str]:
        graph = self._get_graph(child_id)
        return await GraphReasoner(graph=graph, llm=self._llm).identify_gaps()

    async def refresh(self, child_id: str) -> dict:
        graph = self._get_graph(child_id)
        from sociomemory.engine.versioning import VersioningEngine

        stale_ids = await VersioningEngine(graph).recompute_stale()
        return {"stale_nodes": len(stale_ids), "node_ids": stale_ids}

    async def segment_episodes(self, child_id: str) -> dict:
        if self._config.enforce_consent:
            self.privacy.require_consent(child_id, ConsentScope.BEHAVIORAL_PROFILING)
        graph = await self.get_graph(child_id)
        from sociomemory.engine.episodes import EpisodeSegmenter

        return await EpisodeSegmenter(graph).segment()
