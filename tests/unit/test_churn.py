from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.intelligence.churn import (
    CHURN_FEATURE_NAMES,
    MODEL_VERSION,
    PREDICTION_SET_VERSION,
    ChurnService,
    load_artifact,
    score_churn,
    vector_from_features,
)
from telco_digital.intelligence.churn.features import ordered_values
from telco_digital.intelligence.features import CustomerFeatures, GraphFeatures
from telco_digital.intelligence.features.service import FeatureGroup

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


def _features(ref: str, temporal: dict) -> CustomerFeatures:
    return CustomerFeatures(
        customer_id=uuid4(),
        customer_ref=ref,
        as_of=AS_OF,
        computed_at=AS_OF,
        temporal={
            name: FeatureGroup(window_days=30, values=values) for name, values in temporal.items()
        },
        graph=GraphFeatures(available=False, values={}),
        provenance=("test",),
    )


def test_u004_like_vector_is_high_risk() -> None:
    features = _features(
        "U004",
        {
            "usage": {
                "data_mb_30d": 200,
                "data_mb_90d": 200,
                "data_mb_change_ratio": None,
                "event_count_30d": 1,
            },
            "recharge": {"count_30d": 0, "amount_30d": 0, "average_90d": None},
            "service": {
                "complaint_count_90d": 1,
                "open_count": 2,
                "interaction_count_90d": 2,
            },
            "plan": {"subscription_count_365d": 1},
        },
    )
    document = score_churn(features)
    assert document.risk_band == "HIGH"
    assert document.probability >= 0.60
    assert document.model_version == MODEL_VERSION
    assert document.prediction_set_version == PREDICTION_SET_VERSION
    driver_names = {item.feature for item in document.drivers}
    assert driver_names & {
        "complaint_count_90d",
        "open_ticket_count",
        "data_mb_30d",
        "recharge_amount_30d",
        "service_interaction_count_90d",
    }
    assert any("Tenure" in item for item in document.unknowns)


def test_u003_like_vector_is_low_risk() -> None:
    features = _features(
        "U003",
        {
            "usage": {
                "data_mb_30d": 3500,
                "data_mb_90d": 9800,
                "data_mb_change_ratio": 0.02,
                "event_count_30d": 8,
            },
            "recharge": {"count_30d": 2, "amount_30d": 5000, "average_90d": 2500},
            "service": {
                "complaint_count_90d": 0,
                "open_count": 0,
                "interaction_count_90d": 0,
            },
            "loyalty": {"entry_count_90d": 3, "net_points_90d": 400},
        },
    )
    document = score_churn(features)
    assert document.risk_band == "LOW"
    assert document.probability < 0.35


def test_vector_matches_artifact_feature_names() -> None:
    features = _features("U004", {"usage": {"data_mb_30d": 200}})
    vector, _unknowns = vector_from_features(features)
    artifact = load_artifact()
    assert tuple(artifact["feature_names"]) == CHURN_FEATURE_NAMES
    assert set(vector) == set(CHURN_FEATURE_NAMES)
    assert len(ordered_values(vector)) == len(artifact["coefficients"])


def test_naive_as_of_is_rejected() -> None:
    features = _features("U004", {})
    features = features.model_copy(update={"as_of": datetime(2026, 8, 21)})
    with pytest.raises(ValueError, match="timezone-aware"):
        score_churn(features)


@pytest.mark.asyncio
async def test_service_scores_from_features() -> None:
    features = _features(
        "U004",
        {
            "usage": {"data_mb_30d": 200, "event_count_30d": 1},
            "service": {
                "complaint_count_90d": 1,
                "open_count": 2,
                "interaction_count_90d": 2,
            },
        },
    )

    class Features:
        async def calculate(self, customer_ref: str, as_of: datetime):
            return features

    result = await ChurnService(Features()).predict("U004", AS_OF)
    assert result.customer_ref == "U004"
    assert result.risk_band == "HIGH"
    assert result.source == "derived_live"
