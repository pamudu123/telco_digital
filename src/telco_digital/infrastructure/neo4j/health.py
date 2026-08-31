"""Neo4j connectivity probe. No Cypher writes."""

from __future__ import annotations

import asyncio

from neo4j import GraphDatabase

from telco_digital.config import Settings


async def ping_neo4j(settings: Settings) -> bool:
    def _ping() -> bool:
        with GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=1.0,
        ) as driver:
            driver.verify_connectivity()
        return True

    try:
        return await asyncio.to_thread(_ping)
    except Exception:
        return False
