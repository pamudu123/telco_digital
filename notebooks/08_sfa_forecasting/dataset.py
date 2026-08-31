"""Daily retailer demand panel for the capability-08 notebook.

The generative path lives in ``telco_digital.intelligence.forecasting.series``
so training and runtime scoring stay on the same contract.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from telco_digital.intelligence.forecasting.series import (
    HERO_PRODUCT_CODE,
    HERO_RETAILER_REF,
    PRODUCT_COUNT,
    RETAILER_COUNT,
    generate_product_points,
    product_code_for,
)

TRAIN_END = datetime(2026, 7, 24, tzinfo=UTC)
HOLDOUT_END = datetime(2026, 8, 21, tzinfo=UTC)
PANEL_END = datetime(2026, 8, 31, 23, 59, tzinfo=UTC)


def product_frame(retailer_index: int, product_index: int, as_of: datetime = PANEL_END) -> pd.DataFrame:
    points = generate_product_points(retailer_index, product_index, as_of)
    return pd.DataFrame(
        {
            "ds": [datetime(point.day.year, point.day.month, point.day.day, tzinfo=UTC) for point in points],
            "y": [point.demand for point in points],
            "on_hand": [point.on_hand for point in points],
            "retailer_ref": f"RET-{retailer_index:03d}",
            "product_code": product_code_for(product_index),
        }
    )


def hero_frame(as_of: datetime = PANEL_END) -> pd.DataFrame:
    return product_frame(1, 1, as_of)


def panel_frame(as_of: datetime = PANEL_END) -> pd.DataFrame:
    frames = [
        product_frame(retailer, product, as_of)
        for retailer in range(1, RETAILER_COUNT + 1)
        for product in range(1, PRODUCT_COUNT + 1)
    ]
    return pd.concat(frames, ignore_index=True)


def split_hero() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = hero_frame()
    train = frame[frame["ds"] <= TRAIN_END].copy()
    holdout = frame[(frame["ds"] > TRAIN_END) & (frame["ds"] <= HOLDOUT_END)].copy()
    return train, holdout


__all__ = [
    "HERO_PRODUCT_CODE",
    "HERO_RETAILER_REF",
    "HOLDOUT_END",
    "PANEL_END",
    "TRAIN_END",
    "hero_frame",
    "panel_frame",
    "product_frame",
    "split_hero",
]
