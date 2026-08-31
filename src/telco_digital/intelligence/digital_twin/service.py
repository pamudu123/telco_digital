"""Computed digital twins. Not an authoritative table.

``DigitalTwinService.build(entity_id, as_of)`` composes observed state, recent
features, travel memory, graph context, behaviour, churn, recommendations and
persisted warnings. Fraud and SFA demand stay unknown until those capabilities
land. CustomerContext is embedded, not replaced.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.application.commands.commands import GetCustomerStateQuery
from telco_digital.application.queries.dtos import ObservedCustomerState
from telco_digital.application.queries.showcase import FactRecord, Retailer360
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.intelligence.behaviour import (
    BehaviourTrait,
    CustomerBehaviour,
    build_behaviour,
)
from telco_digital.intelligence.churn import CustomerChurn, score_churn
from telco_digital.intelligence.event_memory import CustomerContext, EventMemoryService
from telco_digital.intelligence.features import (
    CustomerFeatures,
    CustomerFeatureService,
    GraphFeatures,
)
from telco_digital.intelligence.features.service import validate_as_of
from telco_digital.intelligence.recommendations import (
    CustomerRecommendation,
    build_recommendation,
)
from telco_digital.intelligence.recommendations.catalogue import CatalogueReader

TWIN_SET_VERSION = "digital-twin-v1"
ENTITY_CUSTOMER = "CUSTOMER"
ENTITY_RETAILER = "RETAILER"

FRAUD_UNKNOWN = "Graph fraud scoring is not implemented (capability 07)."
DEMAND_UNKNOWN = "Retailer demand forecast is not implemented (capability 08)."
DECISION_UNKNOWN = "Next-best action waits for the decision engine (capability 10)."


class ObservedStateReader(Protocol):
    async def get(self, customer_ref: str, as_of: datetime) -> ObservedCustomerState: ...


class FeatureCalculator(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> CustomerFeatures: ...


class EpisodeRecaller(Protocol):
    async def recall(
        self, customer_ref: str, as_of: datetime, *, destination: str | None = None
    ) -> CustomerContext: ...


class RetailerFactsReader(Protocol):
    async def get(self, retailer_ref: str, as_of: datetime) -> Retailer360: ...


class UnitOfWorkStateReader:
    """Adapts CustomerStateService. No SQL is added."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get(self, customer_ref: str, as_of: datetime) -> ObservedCustomerState:
        return await get_customer_state(
            self.uow, GetCustomerStateQuery(customer_ref=customer_ref, as_of=as_of)
        )


class ObservedTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_ref: str
    home_country: str
    country: str
    country_name: str
    country_source: str
    current_plan_code: str | None
    balance_amount: float
    currency: str
    loyalty_points: int
    device_ref: str | None
    active_complaints: int
    trip_duration_known: bool


class RecentTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    usage_mb_30d: float | None = None
    recharge_amount_30d: float | None = None
    recharge_count_30d: int | None = None
    trip_count_365d: int | None = None
    current_destination: str | None = None
    current_destination_known: bool = False
    situation_source: str = "none"


class HistoricalTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_count: int
    top_destination: str | None = None
    top_plan: str | None = None
    top_duration_days: int | None = None
    top_usage_gb: float | None = None
    top_outcome: str | None = None
    match_rank: str | None = None


class RelationshipTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    values: dict[str, int | float | None] = {}
    unknowns: tuple[str, ...] = ()


class InferredTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    traits: tuple[BehaviourTrait, ...] = ()


class PredictedTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    churn_probability: float | None = None
    churn_risk_band: str | None = None
    churn_model_version: str | None = None
    churn_drivers: tuple[str, ...] = ()
    fraud_status: Literal["unknown"] = "unknown"
    demand_status: Literal["unknown"] = "unknown"


class RecommendedTwinFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str | None = None
    primary_plan_code: str | None = None
    alternatives: tuple[str, ...] = ()
    decision_engine: Literal["not_started"] = "not_started"


class CustomerDigitalTwin(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    kind: Literal["CUSTOMER"] = ENTITY_CUSTOMER
    entity_id: str
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    twin_set_version: str = TWIN_SET_VERSION
    observed: ObservedTwinFacts
    recent: RecentTwinFacts
    historical: HistoricalTwinFacts
    relationships: RelationshipTwinFacts
    inferred: InferredTwinFacts
    predicted: PredictedTwinFacts
    unknowns: tuple[str, ...] = ()
    recommended: RecommendedTwinFacts
    warnings: tuple[str, ...] = ()
    customer_context: CustomerContext
    provenance: tuple[str, ...] = (
        "PostgreSQL point-in-time observed facts",
        "Derived features, travel episodes, behaviour traits and catalogue offers",
        "Notebook-trained churn artifact",
        "Digital twins are computed and not persisted",
        "CustomerContext remains the object consumed by recommendation and decisioning",
    )


class RetailerObservedFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    retailer_ref: str
    name: str
    region: str
    status: str
    sale_count: int
    inventory_event_count: int
    last_sale_at: datetime | None = None
    last_inventory_at: datetime | None = None


class RetailerHistoricalFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_quantity: float
    total_amount: float
    product_codes: tuple[str, ...] = ()


class RetailerPredictedFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    forecast: None = None
    stockout_probability: None = None
    status: Literal["unknown"] = "unknown"


class RetailerRecommendedFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: None = None
    status: Literal["unknown"] = "unknown"


class RetailerDigitalTwin(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    kind: Literal["RETAILER"] = ENTITY_RETAILER
    entity_id: str
    retailer_ref: str
    as_of: datetime
    computed_at: datetime
    twin_set_version: str = TWIN_SET_VERSION
    observed: RetailerObservedFacts
    historical: RetailerHistoricalFacts
    predicted: RetailerPredictedFacts
    recommended: RetailerRecommendedFacts
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "PostgreSQL retailer sales and inventory facts",
        "Digital twins are computed and not persisted",
        "Forecast and restock wait for capabilities 08 and 10",
    )


def is_retailer_ref(entity_id: str) -> bool:
    return entity_id.upper().startswith("RET")


def _group_values(features: CustomerFeatures, name: str) -> dict[str, Any]:
    group = features.temporal.get(name)
    return dict(group.values) if group is not None else {}


def _optional_float(values: dict[str, Any], key: str) -> float | None:
    raw = values.get(key)
    if raw is None:
        return None
    return float(raw)


def _optional_int(values: dict[str, Any], key: str) -> int | None:
    raw = values.get(key)
    if raw is None:
        return None
    return int(raw)


def _observed_facts(observed: ObservedCustomerState) -> ObservedTwinFacts:
    return ObservedTwinFacts(
        customer_ref=observed.customer_ref,
        home_country=observed.home_country,
        country=observed.country,
        country_name=observed.country_name,
        country_source=observed.country_source,
        current_plan_code=observed.current_plan_code,
        balance_amount=float(observed.balance_amount),
        currency=observed.currency,
        loyalty_points=observed.loyalty_points,
        device_ref=observed.device_ref,
        active_complaints=observed.active_complaints,
        trip_duration_known=observed.trip_duration_known,
    )


def _recent_facts(features: CustomerFeatures, context: CustomerContext) -> RecentTwinFacts:
    usage = _group_values(features, "usage")
    recharge = _group_values(features, "recharge")
    travel = _group_values(features, "travel")
    situation = context.current_situation
    return RecentTwinFacts(
        usage_mb_30d=_optional_float(usage, "data_mb_30d"),
        recharge_amount_30d=_optional_float(recharge, "amount_30d"),
        recharge_count_30d=_optional_int(recharge, "count_30d"),
        trip_count_365d=_optional_int(travel, "trip_count_365d"),
        current_destination=situation.destination,
        current_destination_known=situation.destination_known,
        situation_source=situation.source,
    )


def _historical_facts(context: CustomerContext) -> HistoricalTwinFacts:
    top = context.matches[0] if context.matches else None
    episode = top.episode if top else None
    usage = None if episode is None else episode.metrics.get("usage_gb")
    return HistoricalTwinFacts(
        episode_count=len(context.historical_episodes),
        top_destination=(
            None if episode is None else episode.destination_name or episode.destination
        ),
        top_plan=None if episode is None else episode.actions.get("plan_selected"),
        top_duration_days=None if episode is None else episode.duration_days,
        top_usage_gb=None if usage is None else float(usage),
        top_outcome=None if episode is None else episode.outcome,
        match_rank=None if top is None else str(top.rank),
    )


def _relationship_facts(graph: GraphFeatures) -> RelationshipTwinFacts:
    return RelationshipTwinFacts(
        available=graph.available,
        values=dict(graph.values),
        unknowns=tuple(graph.unknowns),
    )


def _predicted_facts(churn: CustomerChurn) -> PredictedTwinFacts:
    return PredictedTwinFacts(
        churn_probability=churn.probability,
        churn_risk_band=churn.risk_band,
        churn_model_version=churn.model_version,
        churn_drivers=tuple(item.feature for item in churn.drivers[:3]),
    )


def _recommended_facts(recommendation: CustomerRecommendation) -> RecommendedTwinFacts:
    primary = recommendation.primary
    alternatives = tuple(
        item.plan_code
        for item in recommendation.ranked
        if primary is None or item.plan_code != primary.plan_code
    )
    return RecommendedTwinFacts(
        mode=str(recommendation.mode),
        primary_plan_code=None if primary is None else primary.plan_code,
        alternatives=alternatives,
    )


def _merge_unknowns(
    features: CustomerFeatures,
    context: CustomerContext,
    behaviour: CustomerBehaviour,
    churn: CustomerChurn,
    recommendation: CustomerRecommendation,
) -> tuple[str, ...]:
    items: list[str] = []
    seen: set[str] = set()
    extras = (
        FRAUD_UNKNOWN,
        DEMAND_UNKNOWN,
        DECISION_UNKNOWN,
    )
    for item in (
        *features.unknowns,
        *context.unknowns,
        *behaviour.unknowns,
        *churn.unknowns,
        *recommendation.unknowns,
        *extras,
    ):
        if item not in seen:
            seen.add(item)
            items.append(item)
    return tuple(items)


def assemble_customer_twin(
    observed: ObservedCustomerState,
    features: CustomerFeatures,
    context: CustomerContext,
    behaviour: CustomerBehaviour,
    churn: CustomerChurn,
    recommendation: CustomerRecommendation,
) -> CustomerDigitalTwin:
    """Combine already-computed layers. Does not persist a twin row."""

    validate_as_of(observed.as_of)
    validate_as_of(features.as_of)
    validate_as_of(context.as_of)
    return CustomerDigitalTwin(
        entity_id=observed.customer_ref,
        customer_id=observed.customer_id,
        customer_ref=observed.customer_ref,
        as_of=observed.as_of,
        computed_at=datetime.now(tz=UTC),
        observed=_observed_facts(observed),
        recent=_recent_facts(features, context),
        historical=_historical_facts(context),
        relationships=_relationship_facts(features.graph),
        inferred=InferredTwinFacts(traits=behaviour.traits),
        predicted=_predicted_facts(churn),
        unknowns=_merge_unknowns(features, context, behaviour, churn, recommendation),
        recommended=_recommended_facts(recommendation),
        warnings=tuple(observed.warnings),
        customer_context=context,
    )


def _fact_number(record: FactRecord, key: str) -> float:
    raw = record.detail.get(key)
    if raw is None:
        return 0.0
    return float(raw)


def assemble_retailer_twin(facts: Retailer360) -> RetailerDigitalTwin:
    validate_as_of(facts.as_of)
    sales = facts.sales
    inventory = facts.inventory
    product_codes = tuple(
        dict.fromkeys(
            str(item.detail["product_code"])
            for item in (*sales, *inventory)
            if item.detail.get("product_code")
        )
    )
    return RetailerDigitalTwin(
        entity_id=facts.retailer_ref,
        retailer_ref=facts.retailer_ref,
        as_of=facts.as_of,
        computed_at=datetime.now(tz=UTC),
        observed=RetailerObservedFacts(
            retailer_ref=facts.retailer_ref,
            name=facts.name,
            region=facts.region,
            status=facts.status,
            sale_count=len(sales),
            inventory_event_count=len(inventory),
            last_sale_at=sales[0].occurred_at if sales else None,
            last_inventory_at=inventory[0].occurred_at if inventory else None,
        ),
        historical=RetailerHistoricalFacts(
            total_quantity=round(sum(_fact_number(item, "quantity") for item in sales), 2),
            total_amount=round(sum(_fact_number(item, "amount") for item in sales), 2),
            product_codes=product_codes,
        ),
        predicted=RetailerPredictedFacts(),
        recommended=RetailerRecommendedFacts(),
        unknowns=(DEMAND_UNKNOWN, DECISION_UNKNOWN),
    )


class DigitalTwinService:
    def __init__(
        self,
        state: ObservedStateReader,
        features: CustomerFeatureService | FeatureCalculator,
        memory: EventMemoryService | EpisodeRecaller,
        catalogue: CatalogueReader,
        *,
        retailers: RetailerFactsReader | None = None,
        churn_artifact: dict[str, Any] | None = None,
    ) -> None:
        self.state = state
        self.features = features
        self.memory = memory
        self.catalogue = catalogue
        self.retailers = retailers
        self.churn_artifact = churn_artifact

    async def build(
        self,
        entity_id: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CustomerDigitalTwin | RetailerDigitalTwin:
        validate_as_of(as_of)
        if is_retailer_ref(entity_id):
            return await self.build_retailer(entity_id, as_of)
        return await self.build_customer(entity_id, as_of, destination=destination)

    async def build_customer(
        self,
        customer_ref: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CustomerDigitalTwin:
        validate_as_of(as_of)
        observed = await self.state.get(customer_ref, as_of)
        features = await self.features.calculate(customer_ref, as_of)
        context = await self.memory.recall(customer_ref, as_of, destination=destination)
        behaviour = build_behaviour(features, context.historical_episodes)
        churn = score_churn(features, self.churn_artifact)
        situation = context.current_situation
        country = situation.destination if situation.destination_known else None
        catalogue = await self.catalogue.list_roaming(country_code=country)
        recommendation = build_recommendation(context, catalogue)
        return assemble_customer_twin(
            observed, features, context, behaviour, churn, recommendation
        )

    async def build_retailer(self, retailer_ref: str, as_of: datetime) -> RetailerDigitalTwin:
        validate_as_of(as_of)
        if self.retailers is None:
            raise LookupError("Retailer facts reader is not configured")
        facts = await self.retailers.get(retailer_ref, as_of)
        return assemble_retailer_twin(facts)
