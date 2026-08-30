"""Live capability-02 checks; skipped when provider configuration is absent."""

import os

import pytest

from telco_digital.application.demo_dataset import END_AT
from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.features import (
    FEATURE_SET_VERSION,
    GraphFeatureService,
    TemporalFeatureService,
)

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_temporal_features_are_versioned_and_bounded() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            customer_id, result = await TemporalFeatureService(
                PostgresTemporalFeatureQueries(session)
            ).calculate("U001", END_AT)
    finally:
        await engine.dispose()

    assert customer_id is not None
    assert FEATURE_SET_VERSION == "customer-features-v1"
    assert {
        "usage",
        "recharge",
        "money",
        "plan",
        "travel",
        "service",
        "loyalty",
        "campaign",
    } <= set(result)


@pytest.mark.skipif(not os.environ.get("NEO4J_URI"), reason="NEO4J_URI is required")
@pytest.mark.asyncio
async def test_live_graph_features_and_summary_are_available() -> None:
    queries = Neo4jFeatureQueries(get_settings())
    result = await GraphFeatureService(queries).calculate("U001", END_AT)
    summary = await queries.summary(END_AT)

    assert result.available is True
    assert result.values["customer_graph_degree"] >= 1
    assert summary["projection"] == "poc-v1"
    assert summary["node_counts"]
