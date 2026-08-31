"""Deterministic daily demand expansion used by training and runtime scoring.

Monthly ``sfa.sale`` rows are the recorded facts. Daily demand is a derived
expansion with weekly seasonality, a slow trend, and a late-period surge for
RET-001. Inventory is reconstructed from restock events minus daily demand.
Neither series is a second source of truth.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from telco_digital.application.demo_dataset import START_AT
from telco_digital.intelligence.features.service import validate_as_of

FEATURE_SET_VERSION = "sfa-daily-demand-v1"
FORECAST_SET_VERSION = "retailer-forecast-v1"
MODEL_VERSION = "sfa-forecast-v1"

SERIES_START = START_AT.date()
HERO_AS_OF = date(2026, 8, 21)
HERO_RETAILER_REF = "RET-001"
HERO_PRODUCT_CODE = "POC-PROD-01"
HERO_RETAILER_INDEX = 1
HERO_PRODUCT_INDEX = 1
PRODUCT_COUNT = 4
RETAILER_COUNT = 25
WEEKLY_FACTORS: tuple[float, ...] = (1.08, 1.12, 1.16, 1.10, 1.22, 0.72, 0.60)
SURGE_START = date(2026, 5, 1)
RESTOCK_LAG_START = date(2026, 7, 15)
SURGE_STRENGTH = 1.65
RESTOCK_LAG_FACTOR = 0.69
HEALTHY_RESTOCK_FACTOR = 1.10
STARTING_STOCK = 50.0


@dataclass(frozen=True)
class SalePoint:
    product_code: str
    occurred_at: datetime
    quantity: float


@dataclass(frozen=True)
class InventoryPoint:
    product_code: str
    occurred_at: datetime
    event_type: str
    quantity: float


@dataclass(frozen=True)
class DailyPoint:
    day: date
    demand: float
    on_hand: float


@dataclass(frozen=True)
class ProductHistory:
    product_code: str
    product_name: str
    points: tuple[DailyPoint, ...]


@dataclass(frozen=True)
class RetailerDemandHistory:
    retailer_id: str
    retailer_ref: str
    name: str
    region: str
    status: str
    products: tuple[ProductHistory, ...]


def as_of_date(as_of: datetime) -> date:
    validate_as_of(as_of)
    return as_of.astimezone(UTC).date()


def retailer_index(retailer_ref: str) -> int:
    if retailer_ref.startswith("RET-") and retailer_ref[4:].isdigit():
        return int(retailer_ref[4:])
    raise ValueError(f"Unsupported retailer_ref: {retailer_ref}")


def product_index(product_code: str) -> int:
    if product_code.startswith("POC-PROD-") and product_code[9:].isdigit():
        return int(product_code[9:])
    raise ValueError(f"Unsupported product_code: {product_code}")


def product_code_for(index: int) -> str:
    return f"POC-PROD-{index:02d}"


def daily_demand(retailer: int, product: int, day: date) -> float:
    """Scenario-shaped daily units for one retailer/product."""
    level = 2.05 + 0.10 * ((retailer + product) % 8)
    weekly = WEEKLY_FACTORS[day.weekday()]
    trend = 1.0 + 0.00065 * (day - SERIES_START).days
    surge = 1.0
    if retailer == HERO_RETAILER_INDEX and day >= SURGE_START:
        ramp = min(1.0, (day - SURGE_START).days / 112)
        surge = 1.0 + SURGE_STRENGTH * ramp
    mix = 0.84 + 0.08 * product
    return round(max(0.0, level * weekly * trend * surge * mix), 4)


def restock_quantity(retailer: int, product: int, day: date) -> float:
    upcoming = sum(
        daily_demand(retailer, product, day + timedelta(days=offset)) for offset in range(14)
    )
    if retailer == HERO_RETAILER_INDEX and day >= RESTOCK_LAG_START:
        return round(upcoming * RESTOCK_LAG_FACTOR, 4)
    return round(upcoming * HEALTHY_RESTOCK_FACTOR, 4)


def on_hand_at(retailer: int, product: int, day: date) -> float:
    stock = STARTING_STOCK
    cursor = SERIES_START
    while cursor <= day:
        if cursor.day in {1, 15}:
            stock += restock_quantity(retailer, product, cursor)
        stock = max(0.0, stock - daily_demand(retailer, product, cursor))
        cursor += timedelta(days=1)
    return round(stock, 4)


def date_range(start: date, end: date) -> tuple[date, ...]:
    if end < start:
        return ()
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def generate_product_points(retailer: int, product: int, as_of: datetime) -> tuple[DailyPoint, ...]:
    end = as_of_date(as_of)
    return tuple(
        DailyPoint(
            day=day,
            demand=daily_demand(retailer, product, day),
            on_hand=on_hand_at(retailer, product, day),
        )
        for day in date_range(SERIES_START, end)
    )


def generate_retailer_history(
    retailer_ref: str,
    as_of: datetime,
    *,
    product_codes: Iterable[str] | None = None,
    name: str | None = None,
    region: str = "WESTERN",
    status: str = "ACTIVE",
) -> RetailerDemandHistory:
    index = retailer_index(retailer_ref)
    codes = tuple(product_codes) if product_codes is not None else tuple(
        product_code_for(item) for item in range(1, PRODUCT_COUNT + 1)
    )
    products = tuple(
        ProductHistory(
            product_code=code,
            product_name=f"POC Product {product_index(code):02d}",
            points=generate_product_points(index, product_index(code), as_of),
        )
        for code in codes
    )
    return RetailerDemandHistory(
        retailer_id=retailer_ref,
        retailer_ref=retailer_ref,
        name=name or f"POC Retailer {index:02d}",
        region=region,
        status=status,
        products=products,
    )


def monthly_observed_quantities(sales: Iterable[SalePoint]) -> dict[tuple[int, int, str], float]:
    totals: dict[tuple[int, int, str], float] = {}
    for sale in sales:
        day = sale.occurred_at.astimezone(UTC).date()
        key = (day.year, day.month, sale.product_code)
        totals[key] = totals.get(key, 0.0) + float(sale.quantity)
    return totals


def expand_observed_history(
    retailer_ref: str,
    as_of: datetime,
    *,
    sales: Iterable[SalePoint] = (),
    name: str | None = None,
    region: str = "WESTERN",
    status: str = "ACTIVE",
    product_names: dict[str, str] | None = None,
) -> RetailerDemandHistory:
    """Expand recorded monthly pulses onto the daily shape, then continue the trend.

    Months with observed sales are scaled so the daily sum matches the pulse.
    Days after the last observed month keep the unscaled generative path so a
    rising RET-001 series can continue into August.
    """
    validate_as_of(as_of)
    index = retailer_index(retailer_ref)
    observed = monthly_observed_quantities(sales)
    last_observed: dict[str, date] = {}
    for sale in sales:
        day = sale.occurred_at.astimezone(UTC).date()
        previous = last_observed.get(sale.product_code)
        if previous is None or day > previous:
            last_observed[sale.product_code] = day

    observed_codes = {sale.product_code for sale in sales}
    codes = sorted(observed_codes or {product_code_for(i) for i in range(1, 5)})
    names = product_names or {}
    products: list[ProductHistory] = []
    for code in codes:
        product = product_index(code)
        raw_points = generate_product_points(index, product, as_of)
        scaled: list[DailyPoint] = []
        for point in raw_points:
            key = (point.day.year, point.day.month, code)
            last = last_observed.get(code)
            if key in observed:
                month_days = [
                    item
                    for item in raw_points
                    if item.day.year == point.day.year and item.day.month == point.day.month
                ]
                month_raw = sum(item.demand for item in month_days) or 1.0
                demand = round(point.demand * (observed[key] / month_raw), 4)
            elif last is not None and point.day.replace(day=1) <= last.replace(day=1):
                demand = 0.0
            else:
                demand = point.demand
            scaled.append(DailyPoint(day=point.day, demand=demand, on_hand=point.on_hand))
        products.append(
            ProductHistory(
                product_code=code,
                product_name=names.get(code, f"POC Product {product:02d}"),
                points=tuple(scaled),
            )
        )
    return RetailerDemandHistory(
        retailer_id=retailer_ref,
        retailer_ref=retailer_ref,
        name=name or f"POC Retailer {index:02d}",
        region=region,
        status=status,
        products=tuple(products),
    )


def values_and_dates(points: Iterable[DailyPoint]) -> tuple[list[date], list[float]]:
    days = [item.day for item in points]
    values = [item.demand for item in points]
    return days, values
