from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.intelligence.behaviour import (
    BEHAVIOUR_SET_VERSION,
    BehaviourService,
    assign_traits,
    build_behaviour,
)
from telco_digital.intelligence.event_memory import TravelEpisode
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


def _episode() -> TravelEpisode:
    return TravelEpisode(
        customer_id=uuid4(),
        customer_ref="U001",
        travel_id=uuid4(),
        destination="SG",
        destination_name="Singapore",
        start_at=datetime.fromisoformat("2026-03-10T08:00:00+00:00"),
        end_at=datetime.fromisoformat("2026-03-16T18:00:00+00:00"),
        duration_days=6,
        duration_known=True,
        context={"destination": "SG"},
        actions={"plan_selected": "ROAM_15"},
        outcome="No additional package required",
        metrics={"usage_gb": 11.4, "usage_mb": 11400.0, "duration_days": 6},
    )


def test_u002_is_price_sensitive() -> None:
    features = _features(
        "U002",
        {
            "recharge": {
                "small_recharge_count_30d": 5,
                "frequent_small_recharge_evidence": True,
                "amount_30d": 500,
            }
        },
    )
    traits = {item.trait: item for item in assign_traits(features)}
    assert "PRICE_SENSITIVE" in traits
    assert traits["PRICE_SENSITIVE"].confidence >= 0.7
    assert traits["PRICE_SENSITIVE"].evidence["small_recharge_count_30d"] == 5
    assert "HIGH_VALUE" not in traits


def test_u001_is_traveller_and_heavy_data() -> None:
    features = _features(
        "U001",
        {
            "travel": {"trip_count_365d": 1, "roaming_days_365d": 6},
            "usage": {"data_mb_30d": 0, "data_mb_90d": 0},
        },
    )
    traits = {item.trait for item in assign_traits(features, (_episode(),))}
    assert "FREQUENT_TRAVELLER" in traits
    assert "HEAVY_DATA_USER" in traits


def test_u003_is_high_value() -> None:
    features = _features(
        "U003",
        {"recharge": {"amount_30d": 5000, "small_recharge_count_30d": 0}},
    )
    traits = {item.trait for item in assign_traits(features)}
    assert "HIGH_VALUE" in traits
    assert "PRICE_SENSITIVE" not in traits


def test_u004_declining_engagement_from_complaints() -> None:
    features = _features(
        "U004",
        {
            "usage": {"data_mb_30d": 200, "data_mb_change_ratio": None},
            "service": {"complaint_count_90d": 1, "open_count": 1},
        },
    )
    traits = {item.trait for item in assign_traits(features)}
    assert "DECLINING_ENGAGEMENT" in traits


def test_no_trait_when_evidence_is_missing() -> None:
    document = build_behaviour(_features("U003", {"recharge": {"amount_30d": 0}}))
    assert document.traits == ()
    assert any("No behaviour trait" in item for item in document.unknowns)


def test_naive_as_of_is_rejected() -> None:
    features = _features("U002", {})
    features = features.model_copy(update={"as_of": datetime(2026, 8, 21)})
    with pytest.raises(ValueError, match="timezone-aware"):
        build_behaviour(features)


@pytest.mark.asyncio
async def test_service_uses_features_and_episodes() -> None:
    features = _features(
        "U002",
        {
            "recharge": {
                "small_recharge_count_30d": 5,
                "frequent_small_recharge_evidence": True,
                "amount_30d": 500,
            }
        },
    )

    class Features:
        async def calculate(self, customer_ref: str, as_of: datetime):
            return features

    class Memory:
        async def recall(self, customer_ref: str, as_of: datetime, *, destination=None):
            return type("Recalled", (), {"historical_episodes": ()})()

    result = await BehaviourService(Features(), Memory()).evaluate("U002", AS_OF)
    assert result.behaviour_set_version == BEHAVIOUR_SET_VERSION
    assert result.traits[0].trait == "PRICE_SENSITIVE"
