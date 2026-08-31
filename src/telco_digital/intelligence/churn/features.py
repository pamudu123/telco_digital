"""Shared churn feature-vector contract used by the notebook and the scorer.

Keys are taken from ``customer-features-v1``. Missing numeric values become
``0.0`` and are listed as unknowns so scoring never invents facts.
"""

from __future__ import annotations

from typing import Any

from telco_digital.intelligence.features import CustomerFeatures
from telco_digital.intelligence.features.service import validate_as_of

FEATURE_SET_VERSION = "customer-features-v1"
PREDICTION_SET_VERSION = "customer-churn-v1"
MODEL_VERSION = "churn-lr-v1"

CHURN_FEATURE_NAMES: tuple[str, ...] = (
    "data_mb_30d",
    "data_mb_90d",
    "data_mb_change_ratio",
    "usage_change_unknown",
    "usage_event_count_30d",
    "recharge_count_30d",
    "recharge_amount_30d",
    "recharge_average_90d",
    "small_recharge_count_30d",
    "complaint_count_90d",
    "open_ticket_count",
    "service_interaction_count_90d",
    "campaign_interaction_count_90d",
    "campaign_conversion_count_90d",
    "loyalty_entry_count_90d",
    "loyalty_net_points_90d",
    "subscription_count_365d",
    "trip_count_365d",
)


def _values(features: CustomerFeatures, group: str) -> dict[str, Any]:
    item = features.temporal.get(group)
    return dict(item.values) if item is not None else {}


def _number(values: dict[str, Any], key: str) -> float | None:
    raw = values.get(key)
    if raw is None:
        return None
    return float(raw)


def vector_from_features(features: CustomerFeatures) -> tuple[dict[str, float], tuple[str, ...]]:
    """Project a feature document onto the trained churn keys."""

    validate_as_of(features.as_of)
    usage = _values(features, "usage")
    recharge = _values(features, "recharge")
    service = _values(features, "service")
    campaign = _values(features, "campaign")
    loyalty = _values(features, "loyalty")
    plan = _values(features, "plan")
    travel = _values(features, "travel")

    change_ratio = _number(usage, "data_mb_change_ratio")
    unknowns: list[str] = list(features.unknowns)
    if change_ratio is None:
        unknowns.append(
            "Usage change ratio is unknown because the previous 30-day window is empty."
        )
    if not _values(features, "loyalty"):
        unknowns.append("Loyalty engagement is not present on this feature document.")
    if not _values(features, "campaign"):
        unknowns.append("Campaign engagement is not present on this feature document.")
    unknowns.append("Tenure days are not in customer-features-v1 and are omitted from this score.")

    vector = {
        "data_mb_30d": _number(usage, "data_mb_30d") or 0.0,
        "data_mb_90d": _number(usage, "data_mb_90d") or 0.0,
        "data_mb_change_ratio": 0.0 if change_ratio is None else change_ratio,
        "usage_change_unknown": 1.0 if change_ratio is None else 0.0,
        "usage_event_count_30d": _number(usage, "event_count_30d") or 0.0,
        "recharge_count_30d": _number(recharge, "count_30d") or 0.0,
        "recharge_amount_30d": _number(recharge, "amount_30d") or 0.0,
        "recharge_average_90d": _number(recharge, "average_90d") or 0.0,
        "small_recharge_count_30d": _number(recharge, "small_recharge_count_30d") or 0.0,
        "complaint_count_90d": _number(service, "complaint_count_90d") or 0.0,
        "open_ticket_count": _number(service, "open_count") or 0.0,
        "service_interaction_count_90d": _number(service, "interaction_count_90d") or 0.0,
        "campaign_interaction_count_90d": _number(campaign, "interaction_count_90d") or 0.0,
        "campaign_conversion_count_90d": _number(campaign, "conversion_count_90d") or 0.0,
        "loyalty_entry_count_90d": _number(loyalty, "entry_count_90d") or 0.0,
        "loyalty_net_points_90d": _number(loyalty, "net_points_90d") or 0.0,
        "subscription_count_365d": _number(plan, "subscription_count_365d") or 0.0,
        "trip_count_365d": _number(travel, "trip_count_365d") or 0.0,
    }
    return vector, tuple(dict.fromkeys(unknowns))


def ordered_values(
    vector: dict[str, float], names: tuple[str, ...] = CHURN_FEATURE_NAMES
) -> list[float]:
    missing = [name for name in names if name not in vector]
    if missing:
        raise ValueError(f"Churn vector is missing keys: {missing}")
    return [float(vector[name]) for name in names]
