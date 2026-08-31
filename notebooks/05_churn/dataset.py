"""Synthetic labelled churn rows for the capability-05 notebook.

The five golden seeds are not a training set. Rows follow the same feature
keys as ``telco_digital.intelligence.churn.features.CHURN_FEATURE_NAMES``.
Labels are persona-shaped with a small flip rate so the comparison is a real
classification problem, not a tautology.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from telco_digital.intelligence.churn.features import CHURN_FEATURE_NAMES

RANDOM_STATE = 42
N_ROWS = 1600

# Seed-like vectors used only for notebook evidence tables, not for fitting.
GOLDEN_VECTORS: dict[str, dict[str, float]] = {
    "U001": {
        "data_mb_30d": 0.0,
        "data_mb_90d": 11400.0,
        "data_mb_change_ratio": 0.0,
        "usage_change_unknown": 1.0,
        "usage_event_count_30d": 0.0,
        "recharge_count_30d": 1.0,
        "recharge_amount_30d": 1500.0,
        "recharge_average_90d": 1500.0,
        "small_recharge_count_30d": 0.0,
        "complaint_count_90d": 0.0,
        "open_ticket_count": 0.0,
        "service_interaction_count_90d": 0.0,
        "campaign_interaction_count_90d": 1.0,
        "campaign_conversion_count_90d": 0.0,
        "loyalty_entry_count_90d": 1.0,
        "loyalty_net_points_90d": 200.0,
        "subscription_count_365d": 2.0,
        "trip_count_365d": 1.0,
    },
    "U002": {
        "data_mb_30d": 800.0,
        "data_mb_90d": 2400.0,
        "data_mb_change_ratio": 0.05,
        "usage_change_unknown": 0.0,
        "usage_event_count_30d": 4.0,
        "recharge_count_30d": 5.0,
        "recharge_amount_30d": 500.0,
        "recharge_average_90d": 100.0,
        "small_recharge_count_30d": 5.0,
        "complaint_count_90d": 0.0,
        "open_ticket_count": 0.0,
        "service_interaction_count_90d": 0.0,
        "campaign_interaction_count_90d": 2.0,
        "campaign_conversion_count_90d": 1.0,
        "loyalty_entry_count_90d": 2.0,
        "loyalty_net_points_90d": 80.0,
        "subscription_count_365d": 1.0,
        "trip_count_365d": 0.0,
    },
    "U003": {
        "data_mb_30d": 3500.0,
        "data_mb_90d": 9800.0,
        "data_mb_change_ratio": 0.02,
        "usage_change_unknown": 0.0,
        "usage_event_count_30d": 8.0,
        "recharge_count_30d": 2.0,
        "recharge_amount_30d": 5000.0,
        "recharge_average_90d": 2500.0,
        "small_recharge_count_30d": 0.0,
        "complaint_count_90d": 0.0,
        "open_ticket_count": 0.0,
        "service_interaction_count_90d": 0.0,
        "campaign_interaction_count_90d": 1.0,
        "campaign_conversion_count_90d": 0.0,
        "loyalty_entry_count_90d": 3.0,
        "loyalty_net_points_90d": 400.0,
        "subscription_count_365d": 1.0,
        "trip_count_365d": 0.0,
    },
    "U004": {
        "data_mb_30d": 200.0,
        "data_mb_90d": 200.0,
        "data_mb_change_ratio": 0.0,
        "usage_change_unknown": 1.0,
        "usage_event_count_30d": 1.0,
        "recharge_count_30d": 0.0,
        "recharge_amount_30d": 0.0,
        "recharge_average_90d": 0.0,
        "small_recharge_count_30d": 0.0,
        "complaint_count_90d": 1.0,
        "open_ticket_count": 2.0,
        "service_interaction_count_90d": 2.0,
        "campaign_interaction_count_90d": 0.0,
        "campaign_conversion_count_90d": 0.0,
        "loyalty_entry_count_90d": 0.0,
        "loyalty_net_points_90d": 0.0,
        "subscription_count_365d": 1.0,
        "trip_count_365d": 0.0,
    },
}


def _clip(value: float, low: float, high: float) -> float:
    return float(min(high, max(low, value)))


def _persona_row(rng: np.random.Generator, persona: str) -> dict[str, float]:
    if persona == "DECLINING_ENGAGEMENT":
        change_unknown = float(rng.random() < 0.55)
        return {
            "data_mb_30d": _clip(rng.normal(220, 90), 40, 480),
            "data_mb_90d": _clip(rng.normal(400, 160), 80, 900),
            "data_mb_change_ratio": 0.0
            if change_unknown
            else _clip(rng.normal(-0.55, 0.15), -0.95, -0.1),
            "usage_change_unknown": change_unknown,
            "usage_event_count_30d": float(rng.integers(0, 3)),
            "recharge_count_30d": float(rng.integers(0, 2)),
            "recharge_amount_30d": _clip(rng.normal(80, 70), 0, 250),
            "recharge_average_90d": _clip(rng.normal(120, 80), 0, 300),
            "small_recharge_count_30d": float(rng.integers(0, 2)),
            "complaint_count_90d": float(rng.integers(1, 3)),
            "open_ticket_count": float(rng.integers(1, 3)),
            "service_interaction_count_90d": float(rng.integers(2, 5)),
            "campaign_interaction_count_90d": float(rng.integers(0, 2)),
            "campaign_conversion_count_90d": 0.0,
            "loyalty_entry_count_90d": float(rng.integers(0, 2)),
            "loyalty_net_points_90d": _clip(rng.normal(10, 20), -20, 60),
            "subscription_count_365d": 1.0,
            "trip_count_365d": 0.0,
        }
    if persona == "HIGH_VALUE_QUIET":
        # Matches seed U003: large recent recharge, little or no usage in-window.
        return {
            "data_mb_30d": _clip(rng.normal(80, 120), 0, 400),
            "data_mb_90d": _clip(rng.normal(200, 250), 0, 800),
            "data_mb_change_ratio": 0.0,
            "usage_change_unknown": 1.0,
            "usage_event_count_30d": float(rng.integers(0, 2)),
            "recharge_count_30d": float(rng.integers(1, 3)),
            "recharge_amount_30d": _clip(rng.normal(4800, 600), 2500, 8000),
            "recharge_average_90d": _clip(rng.normal(2400, 400), 1200, 4000),
            "small_recharge_count_30d": 0.0,
            "complaint_count_90d": 0.0,
            "open_ticket_count": 0.0,
            "service_interaction_count_90d": 0.0,
            "campaign_interaction_count_90d": float(rng.integers(0, 2)),
            "campaign_conversion_count_90d": 0.0,
            "loyalty_entry_count_90d": float(rng.integers(1, 4)),
            "loyalty_net_points_90d": _clip(rng.normal(300, 70), 80, 600),
            "subscription_count_365d": 1.0,
            "trip_count_365d": 0.0,
        }
    if persona == "HIGH_VALUE":
        return {
            "data_mb_30d": _clip(rng.normal(3600, 600), 2000, 6000),
            "data_mb_90d": _clip(rng.normal(10000, 1500), 6000, 16000),
            "data_mb_change_ratio": _clip(rng.normal(0.04, 0.08), -0.15, 0.3),
            "usage_change_unknown": 0.0,
            "usage_event_count_30d": float(rng.integers(5, 12)),
            "recharge_count_30d": float(rng.integers(1, 4)),
            "recharge_amount_30d": _clip(rng.normal(4200, 800), 2000, 8000),
            "recharge_average_90d": _clip(rng.normal(2800, 500), 1200, 5000),
            "small_recharge_count_30d": 0.0,
            "complaint_count_90d": 0.0,
            "open_ticket_count": 0.0,
            "service_interaction_count_90d": float(rng.integers(0, 2)),
            "campaign_interaction_count_90d": float(rng.integers(0, 3)),
            "campaign_conversion_count_90d": float(rng.integers(0, 2)),
            "loyalty_entry_count_90d": float(rng.integers(1, 5)),
            "loyalty_net_points_90d": _clip(rng.normal(350, 80), 80, 700),
            "subscription_count_365d": 1.0,
            "trip_count_365d": float(rng.integers(0, 2)),
        }
    if persona == "PRICE_SENSITIVE":
        return {
            "data_mb_30d": _clip(rng.normal(900, 250), 300, 1800),
            "data_mb_90d": _clip(rng.normal(2600, 500), 900, 4500),
            "data_mb_change_ratio": _clip(rng.normal(0.0, 0.12), -0.25, 0.25),
            "usage_change_unknown": 0.0,
            "usage_event_count_30d": float(rng.integers(2, 7)),
            "recharge_count_30d": float(rng.integers(3, 7)),
            "recharge_amount_30d": _clip(rng.normal(480, 80), 250, 800),
            "recharge_average_90d": _clip(rng.normal(140, 40), 60, 250),
            "small_recharge_count_30d": float(rng.integers(3, 7)),
            "complaint_count_90d": float(rng.integers(0, 2)),
            "open_ticket_count": 0.0,
            "service_interaction_count_90d": float(rng.integers(0, 2)),
            "campaign_interaction_count_90d": float(rng.integers(1, 4)),
            "campaign_conversion_count_90d": float(rng.integers(0, 3)),
            "loyalty_entry_count_90d": float(rng.integers(1, 4)),
            "loyalty_net_points_90d": _clip(rng.normal(90, 30), 0, 200),
            "subscription_count_365d": 1.0,
            "trip_count_365d": 0.0,
        }
    if persona == "FREQUENT_TRAVELLER":
        return {
            "data_mb_30d": _clip(rng.normal(1800, 700), 0, 4000),
            "data_mb_90d": _clip(rng.normal(8000, 2000), 2000, 14000),
            "data_mb_change_ratio": _clip(rng.normal(0.1, 0.2), -0.3, 0.6),
            "usage_change_unknown": float(rng.random() < 0.2),
            "usage_event_count_30d": float(rng.integers(0, 6)),
            "recharge_count_30d": float(rng.integers(1, 3)),
            "recharge_amount_30d": _clip(rng.normal(1800, 400), 800, 3200),
            "recharge_average_90d": _clip(rng.normal(1600, 300), 600, 2800),
            "small_recharge_count_30d": 0.0,
            "complaint_count_90d": 0.0,
            "open_ticket_count": 0.0,
            "service_interaction_count_90d": 0.0,
            "campaign_interaction_count_90d": float(rng.integers(0, 3)),
            "campaign_conversion_count_90d": 0.0,
            "loyalty_entry_count_90d": float(rng.integers(0, 3)),
            "loyalty_net_points_90d": _clip(rng.normal(180, 50), 0, 400),
            "subscription_count_365d": float(rng.integers(1, 3)),
            "trip_count_365d": float(rng.integers(1, 3)),
        }
    return {
        "data_mb_30d": _clip(rng.normal(1600, 400), 600, 3000),
        "data_mb_90d": _clip(rng.normal(4800, 900), 1800, 8000),
        "data_mb_change_ratio": _clip(rng.normal(0.01, 0.1), -0.2, 0.25),
        "usage_change_unknown": 0.0,
        "usage_event_count_30d": float(rng.integers(3, 8)),
        "recharge_count_30d": float(rng.integers(1, 3)),
        "recharge_amount_30d": _clip(rng.normal(1200, 250), 400, 2200),
        "recharge_average_90d": _clip(rng.normal(1100, 200), 400, 1800),
        "small_recharge_count_30d": float(rng.integers(0, 2)),
        "complaint_count_90d": 0.0,
        "open_ticket_count": 0.0,
        "service_interaction_count_90d": float(rng.integers(0, 2)),
        "campaign_interaction_count_90d": float(rng.integers(0, 3)),
        "campaign_conversion_count_90d": float(rng.integers(0, 2)),
        "loyalty_entry_count_90d": float(rng.integers(0, 3)),
        "loyalty_net_points_90d": _clip(rng.normal(120, 40), 0, 280),
        "subscription_count_365d": 1.0,
        "trip_count_365d": 0.0,
    }


def _base_label(row: dict[str, float], persona: str) -> int:
    if persona in {"HIGH_VALUE", "HIGH_VALUE_QUIET"}:
        return 0
    if persona == "DECLINING_ENGAGEMENT":
        return 1
    declining = (
        row["data_mb_30d"] < 400
        and row["recharge_amount_30d"] < 200
        and row["complaint_count_90d"] >= 1
        and row["open_ticket_count"] >= 1
    )
    return int(declining)


def build_training_frame(n_rows: int = N_ROWS, *, random_state: int = RANDOM_STATE) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    weights = {
        "DECLINING_ENGAGEMENT": 0.30,
        "HIGH_VALUE": 0.14,
        "HIGH_VALUE_QUIET": 0.12,
        "PRICE_SENSITIVE": 0.16,
        "FREQUENT_TRAVELLER": 0.12,
        "STABLE": 0.16,
    }
    personas = rng.choice(list(weights), size=n_rows, p=list(weights.values()))
    rows: list[dict[str, Any]] = []
    for persona in personas:
        row = _persona_row(rng, str(persona))
        label = _base_label(row, str(persona))
        if rng.random() < 0.04:
            label = 1 - label
        rows.append({**row, "persona": persona, "churned": label})
    frame = pd.DataFrame(rows)
    return frame[["persona", "churned", *CHURN_FEATURE_NAMES]]


def golden_frame() -> pd.DataFrame:
    rows = [{"customer_ref": ref, **values} for ref, values in GOLDEN_VECTORS.items()]
    return pd.DataFrame(rows)
