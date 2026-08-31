"""Scenario: RET-001 rising demand with thin cover → stockout risk + restock."""

from datetime import datetime

import pytest

from telco_digital.intelligence.forecasting import (
    HERO_PRODUCT_CODE,
    forecast_from_generated,
)

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


@pytest.mark.scenario
def test_ret001_inventory_18_and_7d_demand_47_restock() -> None:
    document = forecast_from_generated("RET-001", AS_OF, product_code=HERO_PRODUCT_CODE)
    product = document.products[0]
    assert round(product.on_hand) == 18
    assert 45 <= product.forecast_7d <= 52
    assert product.warning == "STOCKOUT_RISK"
    assert product.action == "RESTOCK"
    assert document.source == "derived_live"


@pytest.mark.scenario
def test_earlier_as_of_excludes_later_surge_cover() -> None:
    earlier = datetime.fromisoformat("2026-04-15T00:00:00+00:00")
    before = forecast_from_generated("RET-001", earlier, product_code=HERO_PRODUCT_CODE)
    after = forecast_from_generated("RET-001", AS_OF, product_code=HERO_PRODUCT_CODE)
    assert before.products[0].forecast_7d < after.products[0].forecast_7d
    assert before.products[0].action == "HOLD"
