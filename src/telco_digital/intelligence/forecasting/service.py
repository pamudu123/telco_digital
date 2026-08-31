"""Point-in-time retailer demand forecasts from a notebook-trained artifact.

Forecasts are derived and are never a source of truth. The served model is the
winner exported by ``notebooks/08_sfa_forecasting/08_sfa_forecasting.ipynb``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.features.service import validate_as_of
from telco_digital.intelligence.forecasting.models import (
    artifact_model_version,
    forecast_from_history,
    load_artifact,
)
from telco_digital.intelligence.forecasting.series import (
    FORECAST_SET_VERSION,
    HERO_PRODUCT_CODE,
    HERO_RETAILER_REF,
    MODEL_VERSION,
    ProductHistory,
    RetailerDemandHistory,
    expand_observed_history,
    generate_retailer_history,
)

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]
SfaAction = Literal["RESTOCK", "MONITOR", "HOLD"]


class DemandPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    day: str
    yhat: float


class ProductForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_code: str
    product_name: str
    on_hand: float
    recent_7d_demand: float
    forecast_7d: float
    daily_forecast: tuple[DemandPoint, ...]
    cover_days: float
    stockout_probability: float
    risk_band: RiskBand
    action: SfaAction
    warning: str | None = None


class RetailerForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    retailer_ref: str
    name: str
    region: str
    as_of: datetime
    computed_at: datetime
    horizon_days: int
    forecast_set_version: str = FORECAST_SET_VERSION
    model_version: str
    model_type: str
    hero_product: str
    products: tuple[ProductForecast, ...]
    stockout_warning: bool
    recommended_action: SfaAction
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "PostgreSQL sfa.sale and sfa.inventory_event facts",
        "Derived daily demand expansion",
        "Notebook-trained Prophet and ARIMA comparison artifact",
        "Forecasts are derived and not persisted",
    )


class DemandHistoryLoader(Protocol):
    async def load(self, retailer_ref: str, as_of: datetime) -> RetailerDemandHistory: ...


def _cover_days(on_hand: float, daily: list[float]) -> float:
    mean = sum(daily) / len(daily) if daily else 0.0
    if mean <= 0:
        return 99.0
    return round(on_hand / mean, 2)


def _stockout_probability(on_hand: float, forecast_sum: float) -> float:
    if forecast_sum <= 0:
        return 0.0
    shortfall = max(0.0, forecast_sum - on_hand)
    return round(min(1.0, shortfall / forecast_sum), 4)


def _risk_and_action(
    on_hand: float, forecast_sum: float, cover_days: float, horizon: int
) -> tuple[RiskBand, SfaAction, str | None]:
    if forecast_sum > on_hand and (on_hand / forecast_sum) < 0.5:
        return "HIGH", "RESTOCK", "STOCKOUT_RISK"
    if forecast_sum > on_hand or cover_days < horizon:
        return "MEDIUM", "RESTOCK", "STOCKOUT_RISK"
    if cover_days < horizon * 1.5:
        return "MEDIUM", "MONITOR", None
    return "LOW", "HOLD", None


def _product_forecast(
    product: ProductHistory,
    *,
    as_of: datetime,
    horizon: int,
    artifact: dict,
) -> ProductForecast:
    history = [point.demand for point in product.points]
    on_hand = product.points[-1].on_hand if product.points else 0.0
    recent = round(sum(history[-7:]), 4)
    predicted = forecast_from_history(history, horizon, artifact)
    forecast_sum = round(sum(predicted), 4)
    cover = _cover_days(on_hand, predicted)
    probability = _stockout_probability(on_hand, forecast_sum)
    band, action, warning = _risk_and_action(on_hand, forecast_sum, cover, horizon)
    start = as_of.astimezone(UTC).date()
    daily = tuple(
        DemandPoint(day=(start + timedelta(days=step)).isoformat(), yhat=value)
        for step, value in enumerate(predicted, start=1)
    )
    return ProductForecast(
        product_code=product.product_code,
        product_name=product.product_name,
        on_hand=round(on_hand, 2),
        recent_7d_demand=recent,
        forecast_7d=forecast_sum,
        daily_forecast=daily,
        cover_days=cover,
        stockout_probability=probability,
        risk_band=band,
        action=action,
        warning=warning,
    )


def score_forecast(
    history: RetailerDemandHistory,
    as_of: datetime,
    *,
    horizon_days: int = 7,
    artifact: dict | None = None,
    product_code: str | None = None,
) -> RetailerForecast:
    validate_as_of(as_of)
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")
    payload = artifact if artifact is not None else load_artifact()
    selected = history.products
    if product_code is not None:
        selected = tuple(item for item in history.products if item.product_code == product_code)
        if not selected:
            raise LookupError(f"Unknown product: {product_code}")
    products = tuple(
        _product_forecast(item, as_of=as_of, horizon=horizon_days, artifact=payload)
        for item in selected
    )
    hero = next((item for item in products if item.product_code == HERO_PRODUCT_CODE), products[0])
    stockout = any(item.warning == "STOCKOUT_RISK" for item in products)
    if any(item.action == "RESTOCK" for item in products):
        action: SfaAction = "RESTOCK"
    elif any(item.action == "MONITOR" for item in products):
        action = "MONITOR"
    else:
        action = "HOLD"
    return RetailerForecast(
        retailer_ref=history.retailer_ref,
        name=history.name,
        region=history.region,
        as_of=as_of,
        computed_at=datetime.now(tz=UTC),
        horizon_days=horizon_days,
        model_version=artifact_model_version(payload),
        model_type=str(payload.get("served_model") or payload.get("model_type") or "prophet"),
        hero_product=hero.product_code,
        products=products,
        stockout_warning=stockout,
        recommended_action=action,
        unknowns=(
            "Daily POS is a derived expansion of monthly sfa.sale pulses",
            "Supplier lead time is unknown",
            "Promotion calendar is not in the recorded facts",
        ),
    )


def forecast_from_generated(
    retailer_ref: str,
    as_of: datetime,
    *,
    horizon_days: int = 7,
    artifact: dict | None = None,
    product_code: str | None = None,
) -> RetailerForecast:
    history = generate_retailer_history(retailer_ref, as_of)
    return score_forecast(
        history,
        as_of,
        horizon_days=horizon_days,
        artifact=artifact,
        product_code=product_code,
    )


class ForecastingService:
    def __init__(
        self,
        queries: DemandHistoryLoader | None = None,
        artifact: dict | None = None,
    ) -> None:
        self.queries = queries
        self.artifact = artifact

    async def forecast(
        self,
        retailer_ref: str,
        as_of: datetime,
        *,
        horizon_days: int = 7,
        product_code: str | None = None,
    ) -> RetailerForecast:
        validate_as_of(as_of)
        if self.queries is None:
            history = generate_retailer_history(retailer_ref, as_of)
        else:
            history = await self.queries.load(retailer_ref, as_of)
        return score_forecast(
            history,
            as_of,
            horizon_days=horizon_days,
            artifact=self.artifact,
            product_code=product_code,
        )


__all__ = [
    "DemandHistoryLoader",
    "ForecastingService",
    "ProductForecast",
    "RetailerForecast",
    "expand_observed_history",
    "forecast_from_generated",
    "score_forecast",
    "HERO_PRODUCT_CODE",
    "HERO_RETAILER_REF",
    "MODEL_VERSION",
]
