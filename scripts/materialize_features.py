#!/usr/bin/env python3
"""Explicitly materialize deterministic customer feature snapshots."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from telco_digital.application.demo_dataset import END_AT, GOLDEN_CUSTOMER_REFS
from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.models import CustomerModel, FeatureSnapshotModel
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.features import (
    CustomerFeatureService,
    GraphFeatureService,
    TemporalFeatureService,
    snapshot_id,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer-ref", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--as-of", default=END_AT.isoformat())
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
    if as_of.tzinfo is None:
        raise ValueError("--as-of must be timezone-aware")
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        refs = list(args.customer_ref)
        if args.all:
            async with factory() as session:
                refs = list((await session.scalars(select(CustomerModel.customer_ref))).all())
        if not refs:
            refs = list(GOLDEN_CUSTOMER_REFS)
        total = 0
        for customer_ref in refs:
            # A fresh short transaction per customer avoids holding a Supabase
            # transaction-pooler connection while Neo4j is queried.
            async with factory() as session:
                service = CustomerFeatureService(
                    TemporalFeatureService(PostgresTemporalFeatureQueries(session)),
                    GraphFeatureService(Neo4jFeatureQueries(settings)),
                )
                features = await service.calculate(customer_ref, as_of)
                payload = features.model_dump(mode="json")
                statement = insert(FeatureSnapshotModel).values(
                    id=snapshot_id(features.customer_id, as_of),
                    entity_type="CUSTOMER",
                    entity_id=features.customer_id,
                    as_of=as_of,
                    feature_set_version=features.feature_set_version,
                    features=payload,
                    created_at=datetime.now(tz=UTC),
                )
                statement = statement.on_conflict_do_update(
                    index_elements=[FeatureSnapshotModel.id],
                    set_={"features": payload, "created_at": datetime.now(tz=UTC)},
                )
                await session.execute(statement)
                await session.commit()
                total += 1
        print({"materialized": total, "as_of": as_of.isoformat()})
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
