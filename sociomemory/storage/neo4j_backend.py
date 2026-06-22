from __future__ import annotations

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)


class Neo4jBackend:
    SCHEMA_QUERIES = [
        "CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:SocioNode) REQUIRE n.id IS UNIQUE",
        "CREATE INDEX node_child_id IF NOT EXISTS FOR (n:SocioNode) ON (n.child_id)",
        "CREATE INDEX node_event_date IF NOT EXISTS FOR (n:SocioNode) ON (n.event_date)",
        "CREATE INDEX node_stale IF NOT EXISTS FOR (n:SocioNode) ON (n.stale)",
        "CREATE INDEX node_child_date IF NOT EXISTS FOR (n:SocioNode) ON (n.child_id, n.event_date)",
    ]

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database  # AuraDB always uses "neo4j"
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
            max_connection_pool_size=50,
        )
        await self._driver.verify_connectivity()
        logger.info("Neo4j connected: %s (db=%s)", self._uri, self._database)

    def _is_aura(self) -> bool:
        return "databases.neo4j.io" in self._uri or self._uri.startswith("neo4j+s://")

    async def init_schema(self) -> None:
        for q in self.SCHEMA_QUERIES:
            try:
                await self.run_write(q)
            except Exception as exc:
                logger.debug("Schema query skipped (%s): %s", exc, q[:60])

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j not connected. Call connect() first.")
        return self._driver

    async def run(self, query: str, **params: Any) -> list[dict]:
        async with self.driver.session(database=self._database) as session:
            result = await session.run(query, **params)
            return [dict(record) async for record in result]

    async def run_write(self, query: str, **params: Any) -> list[dict]:
        async with self.driver.session(database=self._database) as session:
            result = await session.run(query, **params)
            return [dict(record) async for record in result]

    async def run_in_transaction(self, queries: list[tuple[str, dict]]) -> None:
        async with self.driver.session(database=self._database) as session:
            async with await session.begin_transaction() as tx:
                for query, params in queries:
                    await tx.run(query, **params)
                await tx.commit()

    async def health_check(self) -> bool:
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False
