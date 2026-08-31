from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from telco_digital.application.queries.dtos import ObservedCustomerState
from telco_digital.application.queries.showcase import FactRecord, ProvenanceBlock, Retailer360
from telco_digital.intelligence.behaviour import build_behaviour
from telco_digital.intelligence.churn import score_churn
from telco_digital.intelligence.digital_twin import (
    TWIN_SET_VERSION,
    DigitalTwinService,
    assemble_customer_twin,
    assemble_retailer_twin,
    is_retailer_ref,
)
from telco_digital.intelligence.event_memory import (
    CustomerContext,
    EpisodeMatch,
    MatchRank,
    TravelEpisode,
    TravelSituation,
)
from telco_digital.intelligence.features import CustomerFeatures, GraphFeatures
from telco_digital.intelligence.features.service import FeatureGroup
from telco_digital.intelligence.recommendations import CataloguePlan, DecisionMode, build_recommendation

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")
CUSTOMER_ID = uuid4()

CATALOGUE = (
    CataloguePlan(
        plan_code="ROAM_5",
        name="Roaming 5GB",
        plan_type="ROAMING",
        data_mb=5120,
        validity_days=5,
        price=150,
        currency="LKR",
        country_code="SG",
    ),
    CataloguePlan(
        plan_code="ROAM_15",
        name="Roaming 15GB",
        plan_type="ROAMING",
        data_mb=15360,
        validity_days=15,
        price=350,
        currency="LKR",
        country_code="SG",
    ),
    CataloguePlan(
        plan_code="ROAM_30",
        name="Roaming 30GB",
        plan_type="ROAMING",
        data_mb=30720,
        validity_days=30,
        price=600,
        currency="LKR",
        country_code="SG",
    ),
)


def _episode() -> TravelEpisode:
    return TravelEpisode(
        customer_id=CUSTOMER_ID,
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


def _context() -> CustomerContext:
    episode = _episode()
    return CustomerContext(
        customer_id=CUSTOMER_ID,
        customer_ref="U001",
        as_of=AS_OF,
        computed_at=AS_OF,
        current_situation=TravelSituation(
            destination="SG",
            destination_name="Singapore",
            destination_known=True,
            duration_known=False,
            source="query",
        ),
        historical_episodes=(episode,),
        matches=(
            EpisodeMatch(
                episode=episode,
                rank=MatchRank.SAME_CUSTOMER_SAME_SITUATION,
                similarity=0.9,
                reasons=("Same destination",),
            ),
        ),
        unknowns=("Trip duration is unknown; offers are ranked as duration scenarios.",),
    )


def _features(ref: str = "U001", *, temporal: dict | None = None) -> CustomerFeatures:
    values = temporal or {
        "usage": {"data_mb_30d": 3200.0, "data_mb_90d": 8000.0},
        "recharge": {"amount_30d": 1500.0, "count_30d": 2},
        "travel": {"trip_count_365d": 1, "roaming_days_365d": 6},
    }
    return CustomerFeatures(
        customer_id=CUSTOMER_ID,
        customer_ref=ref,
        as_of=AS_OF,
        computed_at=AS_OF,
        temporal={
            name: FeatureGroup(window_days=30, values=group) for name, group in values.items()
        },
        graph=GraphFeatures(
            available=True,
            values={"shared_device_customer_count": 1},
        ),
        provenance=("test",),
    )


def _observed(ref: str = "U001", *, warnings: list[str] | None = None) -> ObservedCustomerState:
    return ObservedCustomerState(
        customer_id=CUSTOMER_ID,
        customer_ref=ref,
        as_of=AS_OF,
        home_country="LK",
        home_country_name="Sri Lanka",
        country="LK",
        country_name="Sri Lanka",
        country_source="home",
        current_plan_code="PLAN_A",
        balance_amount=Decimal("850"),
        currency="LKR",
        device_ref="D001",
        active_complaints=0,
        trip_duration_known=True,
        warnings=warnings or [],
    )


def _u001_twin():
    features = _features()
    context = _context()
    return assemble_customer_twin(
        _observed(),
        features,
        context,
        build_behaviour(features, context.historical_episodes),
        score_churn(features),
        build_recommendation(context, CATALOGUE),
    )


def test_u001_twin_composes_locked_sections() -> None:
    twin = _u001_twin()
    assert twin.kind == "CUSTOMER"
    assert twin.twin_set_version == TWIN_SET_VERSION
    assert twin.source == "derived_live"
    assert twin.observed.current_plan_code == "PLAN_A"
    assert twin.observed.balance_amount == 850.0
    assert twin.recent.usage_mb_30d == 3200.0
    assert twin.recent.current_destination == "SG"
    assert twin.historical.top_plan == "ROAM_15"
    assert twin.historical.top_duration_days == 6
    assert twin.historical.top_usage_gb == 11.4
    assert twin.relationships.available is True
    traits = {item.trait for item in twin.inferred.traits}
    assert "FREQUENT_TRAVELLER" in traits
    assert "HEAVY_DATA_USER" in traits
    assert twin.predicted.churn_risk_band in {"LOW", "MEDIUM", "HIGH"}
    assert twin.predicted.fraud_status == "unknown"
    assert twin.predicted.demand_status == "unknown"
    assert twin.recommended.mode == DecisionMode.SCENARIO_BASED
    assert twin.recommended.primary_plan_code == "ROAM_15"
    assert "ROAM_5" in twin.recommended.alternatives
    assert "ROAM_30" in twin.recommended.alternatives
    assert twin.customer_context.matches[0].episode.actions["plan_selected"] == "ROAM_15"
    assert any("fraud" in item.lower() for item in twin.unknowns)
    assert any("not persisted" in item.lower() for item in twin.provenance)


def test_warnings_are_copied_from_observed_facts() -> None:
    features = _features()
    context = _context()
    twin = assemble_customer_twin(
        _observed(warnings=["IMPOSSIBLE_TRAVEL"]),
        features,
        context,
        build_behaviour(features, context.historical_episodes),
        score_churn(features),
        build_recommendation(context, CATALOGUE),
    )
    assert twin.warnings == ("IMPOSSIBLE_TRAVEL",)


def test_retailer_twin_keeps_forecast_unknown() -> None:
    as_of = AS_OF
    provenance = ProvenanceBlock(
        source="live_database",
        as_of=as_of,
        dataset_version="poc-v1",
        table="sfa.sale",
    )
    facts = Retailer360(
        source="live_database",
        as_of=as_of,
        dataset_version="poc-v1",
        queried_at=as_of,
        retailer_ref="RET-001",
        name="Colombo Central",
        region="Western",
        status="ACTIVE",
        sales=(
            FactRecord(
                kind="sale",
                occurred_at=as_of,
                summary="Starter pack: 47 units, 18800",
                detail={"product_code": "SP-01", "quantity": 47, "amount": "18800"},
                provenance=provenance,
            ),
        ),
        inventory=(
            FactRecord(
                kind="inventory",
                occurred_at=as_of,
                summary="Starter pack: STOCK 18",
                detail={"product_code": "SP-01", "event_type": "STOCK", "quantity": 18},
                provenance=provenance,
            ),
        ),
    )
    twin = assemble_retailer_twin(facts)
    assert twin.kind == "RETAILER"
    assert twin.observed.sale_count == 1
    assert twin.historical.total_quantity == 47.0
    assert twin.historical.total_amount == 18800.0
    assert twin.predicted.status == "unknown"
    assert twin.predicted.forecast is None
    assert twin.recommended.status == "unknown"
    assert any("forecast" in item.lower() for item in twin.unknowns)


def test_naive_as_of_is_rejected() -> None:
    features = _features()
    context = _context().model_copy(update={"as_of": datetime(2026, 8, 20, 12)})
    with pytest.raises(ValueError, match="timezone-aware"):
        assemble_customer_twin(
            _observed(),
            features,
            context,
            build_behaviour(features, _context().historical_episodes),
            score_churn(features),
            build_recommendation(_context(), CATALOGUE),
        )


def test_is_retailer_ref() -> None:
    assert is_retailer_ref("RET-001") is True
    assert is_retailer_ref("U001") is False


@pytest.mark.asyncio
async def test_service_dispatches_customer_and_retailer() -> None:
    features = _features()
    context = _context()
    observed = _observed()
    as_of = AS_OF
    provenance = ProvenanceBlock(
        source="live_database",
        as_of=as_of,
        dataset_version="poc-v1",
        table="sfa.sale",
    )
    retailer = Retailer360(
        source="live_database",
        as_of=as_of,
        dataset_version="poc-v1",
        queried_at=as_of,
        retailer_ref="RET-001",
        name="Colombo Central",
        region="Western",
        status="ACTIVE",
        sales=(),
        inventory=(),
    )

    class State:
        async def get(self, customer_ref: str, as_of_value: datetime):
            assert customer_ref == "U001"
            return observed

    class Features:
        async def calculate(self, customer_ref: str, as_of_value: datetime):
            return features

    class Memory:
        async def recall(self, customer_ref: str, as_of_value: datetime, *, destination=None):
            assert destination == "SG"
            return context

    class Catalogue:
        async def list_roaming(self, *, country_code: str | None):
            assert country_code == "SG"
            return CATALOGUE

    class Retailers:
        async def get(self, retailer_ref: str, as_of_value: datetime):
            assert retailer_ref == "RET-001"
            return retailer

    service = DigitalTwinService(State(), Features(), Memory(), Catalogue(), retailers=Retailers())
    customer = await service.build("U001", AS_OF, destination="SG")
    store = await service.build("RET-001", AS_OF)
    assert customer.recommended.primary_plan_code == "ROAM_15"
    assert store.kind == "RETAILER"
    assert store.predicted.status == "unknown"
