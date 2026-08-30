#!/usr/bin/env python3
"""Idempotently rebuild the current Neo4j projection from PostgreSQL facts."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.projector import GraphProjector, GraphSnapshot
from telco_digital.infrastructure.neo4j.repository import GraphRepository
from telco_digital.infrastructure.postgres.models import (
    AccountModel,
    CustomerDeviceModel,
    CustomerModel,
    DeviceModel,
    PlanModel,
    SubscriptionModel,
)


def _neo4j_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


async def load_snapshot() -> GraphSnapshot:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async def rows(model: Any) -> list[dict[str, Any]]:
            for attempt in range(1, 4):
                try:
                    async with engine.connect() as connection:
                        result = await connection.execute(select(model.__table__))
                        return [
                            {key: _neo4j_value(value) for key, value in row.items()}
                            for row in result.mappings()
                        ]
                except DBAPIError:
                    if attempt == 3:
                        raise
                    await asyncio.sleep(attempt)
            raise AssertionError("unreachable")

        return GraphSnapshot(
            customers=await rows(CustomerModel),
            accounts=await rows(AccountModel),
            devices=await rows(DeviceModel),
            customer_devices=await rows(CustomerDeviceModel),
            plans=await rows(PlanModel),
            subscriptions=await rows(SubscriptionModel),
        )
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
