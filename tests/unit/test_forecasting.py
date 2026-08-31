from datetime import datetime

import pytest

from telco_digital.intelligence.forecasting import (
    HERO_PRODUCT_CODE,
    MODEL_VERSION,
    forecast_from_generated,
    load_artifact,
)
from telco_digital.intelligence.forecasting.series import as_of_date

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


def test_ret001_hero_product_is_high_stockout() -> None:
    document = forecast_from_generated("RET-001", AS_OF, product_code=HERO_PRODUCT_CODE)
    product = document.products[0]
    assert document.retailer_ref == "RET-001"
    assert document.model_version == MODEL_VERSION
    assert 16 <= product.on_hand <= 21
    assert 40 <= product.forecast_7d <= 60
    assert product.forecast_7d > product.on_hand
    assert product.risk_band == "HIGH"
    assert product.action == "RESTOCK"
    assert product.warning == "STOCKOUT_RISK"
    assert document.recommended_action == "RESTOCK"
    assert document.stockout_warning is True


def test_stable_retailer_stays_hold() -> None:
    document = forecast_from_generated("RET-003", AS_OF, product_code=HERO_PRODUCT_CODE)
    product = document.products[0]
    assert product.forecast_7d < product.on_hand
    assert product.risk_band == "LOW"
    assert product.action == "HOLD"
    assert product.warning is None


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        forecast_from_generated("RET-001", datetime(2026, 8, 21))


def test_as_of_date_matches_contract() -> None:
    assert as_of_date(AS_OF).isoformat() == "2026-08-21"


def test_artifact_exposes_prophet_and_arima() -> None:
    artifact = load_artifact()
    assert "prophet" in artifact
    assert "arima" in artifact
    assert "prophet" in artifact["comparison"]
    assert "arima" in artifact["comparison"]
    assert artifact["served_model"] in {"prophet", "arima"}
