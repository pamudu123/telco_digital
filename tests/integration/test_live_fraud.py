"""Live capability-07 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.fraud import Neo4jGraphFraudQueries
from telco_digital.infrastructure.postgres.fraud import PostgresTransactionRiskQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.fraud import FraudService

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or not os.environ.get("NEO4J_URI"),
    reason="DATABASE_URL and NEO4J_URI are required",
)
@pytest.mark.asyncio
async def test_live_fraud_marks_u009_high_and_u003_low() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    settings = get_settings()
    try:
        async with factory() as session:
            service = FraudService(
                PostgresTransactionRiskQueries(session),
                Neo4jGraphFraudQueries(settings),
            )
            high = await service.evaluate("U009", AS_OF)
            low = await service.evaluate("U003", AS_OF)
    finally:
        await engine.dispose()

    assert high.customer_ref == "U009"
    assert high.risk_band == "HIGH"
    assert high.graph_available
    assert high.transaction_risk < high.graph_risk
    assert {rule.code for rule in high.rules if rule.fired} >= {
        "WALLET_FUNNEL",
        "KNOWN_FRAUD_WITHIN_2_HOPS",
    }
    assert low.customer_ref == "U003"
    assert low.risk_band == "LOW"
