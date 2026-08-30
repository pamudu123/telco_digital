"""PostgreSQL integration for the read-only showcase. Skipped unless DATABASE_URL is set."""

import os
from datetime import UTC, datetime, timedelta

import pytest

from telco_digital.application.demo_dataset import END_AT, expected_generated_row_count
from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries

pytestmark = pytest.mark.integration

requires_postgres = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not exported — configure PostgreSQL before running integration tests",
)


@requires_postgres
@pytest.mark.asyncio
async def test_generated_rows_are_not_full_table_sums() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            queries = PostgresShowcaseQueries(session)
            overview = await queries.overview(as_of=END_AT, queried_at=datetime.now(tz=UTC))
    finally:
        await engine.dispose()

    if overview.generated_rows == 0:
        pytest.skip("capability-00 dataset is not loaded")

    assert overview.source == "live_database"
    assert overview.generated_rows == expected_generated_row_count()
    assert overview.total_database_rows >= overview.generated_rows
    assert (
        overview.generated_rows != overview.total_database_rows or overview.total_customers >= 1005
    )


@requires_postgres
@pytest.mark.asyncio
async def test_as_of_excludes_later_customer_and_sfa_events() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    cutoff = datetime(2025, 10, 1, tzinfo=UTC)
    try:
        async with factory() as session:
            queries = PostgresShowcaseQueries(session)
            personas = await queries.list_personas()
            present = {item.customer_ref: item.present for item in personas}
            if not present.get("U006"):
                pytest.skip("capability-00 dataset is not loaded")
            from telco_digital.application.commands.commands import GetCustomerStateQuery
            from telco_digital.application.services.customer_state import get_customer_state
            from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork

            uow = SqlAlchemyUnitOfWork(factory)
            observed = await get_customer_state(
                uow, GetCustomerStateQuery(customer_ref="U006", as_of=cutoff)
            )
            facts = await queries.customer_facts(observed, queried_at=datetime.now(tz=UTC))
            retailer = await queries.retailer_facts(
                "RET-001", as_of=cutoff, queried_at=datetime.now(tz=UTC)
            )
    finally:
        await engine.dispose()

    later = cutoff + timedelta(days=1)
    for collection in (
        facts.usage,
        facts.recharges,
        facts.loyalty,
        facts.campaigns,
        facts.wallet,
        facts.service_interactions,
    ):
        assert all(item.occurred_at is None or item.occurred_at <= cutoff for item in collection)
    assert all(item.occurred_at is None or item.occurred_at <= cutoff for item in facts.travels)
    assert retailer is not None
    assert all(item.occurred_at is None or item.occurred_at <= cutoff for item in retailer.sales)
    assert all(
        item.occurred_at is None or item.occurred_at <= cutoff for item in retailer.inventory
    )
    assert later > cutoff
