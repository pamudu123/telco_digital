#!/usr/bin/env python3
"""Idempotently rebuild the current Neo4j projection from PostgreSQL facts."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.projector import GraphProjector, GraphSnapshot
from telco_digital.infrastructure.neo4j.repository import GraphRepository
from telco_digital.infrastructure.postgres.graph_snapshot import load_graph_snapshot
from telco_digital.infrastructure.postgres.session import create_engine


async def load_snapshot() -> GraphSnapshot:
    engine = create_engine(get_settings())
    try:
        return await load_graph_snapshot(engine)
    finally:
        await engine.dispose()


async def main() -> None:
    settings = get_settings()
    snapshot = await load_snapshot()
    source_counts = {name: len(rows) for name, rows in asdict(snapshot).items()}
    print("PostgreSQL snapshot:", source_counts)

    with GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    ) as driver:
        driver.verify_connectivity()
        counts = GraphProjector(GraphRepository(driver)).rebuild(snapshot)

    print("Neo4j projection:", counts)


if __name__ == "__main__":
    asyncio.run(main())
