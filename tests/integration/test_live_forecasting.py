"""Live capability-08 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.forecasting import PostgresRetailerDemandQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.forecasting import HERO_PRODUCT_CODE, ForecastingService

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_forecast_marks_ret001_stockout() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            result = await ForecastingService(PostgresRetailerDemandQueries(session)).forecast(
                "RET-001",
                AS_OF,
                product_code=HERO_PRODUCT_CODE,
            )
    finally:
        await engine.dispose()

    product = result.products[0]
    assert result.retailer_ref == "RET-001"
    assert product.action == "RESTOCK"
    assert product.warning == "STOCKOUT_RISK"
    assert product.forecast_7d > product.on_hand
