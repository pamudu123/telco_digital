"""Uncertainty-aware travel recommendations from the real catalogue.

Do not map ``model → plan``. Candidates are scored from event memory and
catalogue constraints. Predictions such as churn do not invent an offer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.event_memory import (
    CustomerContext,
    EventMemoryService,
    TravelEpisode,
    TravelSituation,
)
from telco_digital.intelligence.features.service import validate_as_of
from telco_digital.intelligence.recommendations.catalogue import CataloguePlan, CatalogueReader

RECOMMENDATION_SET_VERSION = "customer-recommendations-v1"
MB_PER_GB = 1000.0

UncertaintyStatus = Literal["known", "inferred", "predicted", "unknown"]


class DecisionMode(StrEnum):
    SINGLE_RECOMMENDATION = "SINGLE_RECOMMENDATION"
    RANKED_OPTIONS = "RANKED_OPTIONS"
    SCENARIO_BASED = "SCENARIO_BASED"
    ASK_FOR_INFORMATION = "ASK_FOR_INFORMATION"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"


class UncertaintyFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: UncertaintyStatus
    value: str | None = None
    note: str | None = None


class RankedOffer(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_code: str
    plan_name: str
    plan_type: str
    data_mb: int
    validity_days: int
    price: float
    currency: str
    country_code: str | None = None
    score: float
    confidence: float
    scenario_label: str
    scenario_days: tuple[int, int]
    reasons: tuple[str, ...]
    in_catalogue: bool = True


class CustomerRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    recommendation_set_version: str = RECOMMENDATION_SET_VERSION
    mode: DecisionMode
    primary: RankedOffer | None = None
    ranked: tuple[RankedOffer, ...] = ()
    uncertainty: tuple[UncertaintyFact, ...] = ()
    unknowns: tuple[str, ...] = ()
    evidence: dict[str, str | float | int | None] = {}
    provenance: tuple[str, ...] = (
        "PostgreSQL catalogue and point-in-time travel facts",
        "Derived travel episodes",
        "Recommendations are derived and not persisted",
        "No plan is invented outside the catalogue",
    )


class EpisodeRecaller(Protocol):
    async def recall(
        self, customer_ref: str, as_of: datetime, *, destination: str | None = None
    ) -> CustomerContext: ...


def scenario_for_plan(plan: CataloguePlan) -> tuple[int, int, str]:
    """Map catalogue validity onto the locked travel scenario bands."""

    if plan.validity_days <= 5:
        return (1, 3, "1–3 days")
    if plan.validity_days <= 15:
        return (4, 7, "4–7 days")
    return (8, 14, "8–14 days")


def generate_candidates(
    catalogue: tuple[CataloguePlan, ...],
    *,
    destination: str | None,
) -> tuple[CataloguePlan, ...]:
    offers: list[CataloguePlan] = []
    for plan in catalogue:
        if not plan.active:
            continue
        if plan.plan_type != "ROAMING":
            continue
        if destination and plan.country_code not in (None, destination):
            continue
        offers.append(plan)
    return tuple(offers)


def _historical_plan(episode: TravelEpisode | None) -> str | None:
    if episode is None:
        return None
    code = episode.actions.get("plan_selected")
    return str(code) if code else None


def _usage_mb(episode: TravelEpisode | None) -> float | None:
    if episode is None:
        return None
    raw = episode.metrics.get("usage_mb")
    if raw is not None:
        return float(raw)
    usage_gb = episode.metrics.get("usage_gb")
    if usage_gb is None:
        return None
    return float(usage_gb) * MB_PER_GB


def score_offer(
    plan: CataloguePlan,
    situation: TravelSituation,
    episode: TravelEpisode | None,
) -> RankedOffer:
    low, high, label = scenario_for_plan(plan)
    reasons: list[str] = ["Present in the active catalogue"]
    score = 0.10
    historical_plan = _historical_plan(episode)
    if historical_plan == plan.plan_code:
        score += 0.50
        reasons.append(f"Same plan as the retrieved {episode.destination_name} episode")
    duration = situation.duration_days if situation.duration_known else None
    inferred_duration = episode.duration_days if episode and episode.duration_known else None
    compare_days = duration if duration is not None else inferred_duration
    if compare_days is not None and low <= compare_days <= high:
        score += 0.25
        source = "known" if duration is not None else "historical"
        reasons.append(f"Fits the {label} {source} duration band")
    usage_mb = _usage_mb(episode)
    if usage_mb is not None:
        if usage_mb <= plan.data_mb:
            score += 0.15
            reasons.append("Catalogue data allowance covers historical usage")
        else:
            score -= 0.20
            reasons.append("Historical usage exceeds this catalogue allowance")
    if situation.destination and plan.country_code == situation.destination:
        score += 0.05
        reasons.append("Catalogue country matches the destination")
    score = round(max(0.0, min(score, 1.0)), 4)
    confidence = round(min(0.95, 0.45 + score * 0.5), 2)
    if not situation.duration_known:
        confidence = min(confidence, 0.82)
    return RankedOffer(
        plan_code=plan.plan_code,
        plan_name=plan.name,
        plan_type=plan.plan_type,
        data_mb=plan.data_mb,
        validity_days=plan.validity_days,
        price=plan.price,
        currency=plan.currency,
        country_code=plan.country_code,
        score=score,
        confidence=confidence,
        scenario_label=label,
        scenario_days=(low, high),
        reasons=tuple(reasons),
    )


def decide_mode(
    situation: TravelSituation,
    ranked: tuple[RankedOffer, ...],
) -> DecisionMode:
    if not situation.destination_known:
        return DecisionMode.ASK_FOR_INFORMATION
    if not ranked:
        return DecisionMode.NO_RECOMMENDATION
    if not situation.duration_known:
        return DecisionMode.SCENARIO_BASED
    if len(ranked) == 1 or ranked[0].score - ranked[1].score >= 0.30:
        return DecisionMode.SINGLE_RECOMMENDATION
    return DecisionMode.RANKED_OPTIONS


def assess_uncertainty(
    situation: TravelSituation,
    episode: TravelEpisode | None,
    ranked: tuple[RankedOffer, ...],
) -> tuple[UncertaintyFact, ...]:
    facts = [
        UncertaintyFact(
            name="destination",
            status="known" if situation.destination_known else "unknown",
            value=situation.destination_name or situation.destination,
        ),
        UncertaintyFact(
            name="trip_duration",
            status="known" if situation.duration_known else "unknown",
            value=None if not situation.duration_known else f"{situation.duration_days} days",
            note=None
            if situation.duration_known
            else "Open or query situations keep duration unknown.",
        ),
        UncertaintyFact(
            name="historical_duration",
            status="inferred" if episode and episode.duration_known else "unknown",
            value=None
            if not (episode and episode.duration_known)
            else f"{episode.duration_days} days",
        ),
        UncertaintyFact(
            name="historical_plan",
            status="inferred" if _historical_plan(episode) else "unknown",
            value=_historical_plan(episode),
        ),
        UncertaintyFact(
            name="historical_usage",
            status="inferred" if _usage_mb(episode) is not None else "unknown",
            value=None if episode is None else f"{episode.metrics.get('usage_gb')} GB",
        ),
        UncertaintyFact(
            name="catalogue",
            status="known" if ranked else "unknown",
            value=f"{len(ranked)} roaming offers",
        ),
        UncertaintyFact(
            name="churn_offer_rule",
            status="unknown",
            note="Churn is not used to invent or discount a catalogue plan.",
        ),
    ]
    return tuple(facts)


def _unknowns(
    situation: TravelSituation,
    ranked: tuple[RankedOffer, ...],
    mode: DecisionMode,
) -> tuple[str, ...]:
    items: list[str] = []
    if not situation.destination_known:
        items.append("Destination is unknown; no roam plan can be ranked.")
    elif situation.destination_known and not situation.duration_known:
        items.append("Trip duration is unknown; offers are ranked as duration scenarios.")
    if mode == DecisionMode.NO_RECOMMENDATION:
        items.append("No active roaming catalogue offer matches this destination.")
    if not ranked and situation.destination_known:
        items.append("The catalogue does not contain an invented fallback plan.")
    items.append("Chosen offer and outcome are not recorded in this capability.")
    return tuple(items)


def build_recommendation(
    context: CustomerContext,
    catalogue: tuple[CataloguePlan, ...],
) -> CustomerRecommendation:
    validate_as_of(context.as_of)
    situation = context.current_situation
    top_match = context.matches[0] if context.matches else None
    episode = top_match.episode if top_match else None
    destination = situation.destination if situation.destination_known else None
    candidates = generate_candidates(catalogue, destination=destination)
    ranked = tuple(
        sorted(
            (score_offer(plan, situation, episode) for plan in candidates),
            key=lambda item: (-item.score, item.plan_code),
        )
    )
    mode = decide_mode(situation, ranked)
    evidence: dict[str, str | float | int | None] = {
        "destination": destination,
        "duration_known": situation.duration_known,
        "duration_days": situation.duration_days,
        "situation_source": situation.source,
        "historical_plan": _historical_plan(episode),
        "historical_duration_days": episode.duration_days if episode else None,
        "historical_usage_gb": None if episode is None else episode.metrics.get("usage_gb"),
    }
    return CustomerRecommendation(
        customer_id=context.customer_id,
        customer_ref=context.customer_ref,
        as_of=context.as_of,
        computed_at=datetime.now(tz=UTC),
        mode=mode,
        primary=ranked[0] if ranked and mode != DecisionMode.ASK_FOR_INFORMATION else None,
        ranked=ranked if mode != DecisionMode.ASK_FOR_INFORMATION else (),
        uncertainty=assess_uncertainty(situation, episode, ranked),
        unknowns=_unknowns(situation, ranked, mode),
        evidence=evidence,
    )


class RecommendationService:
    def __init__(
        self,
        memory: EventMemoryService | EpisodeRecaller,
        catalogue: CatalogueReader,
    ) -> None:
        self.memory = memory
        self.catalogue = catalogue

    async def recommend(
        self,
        customer_ref: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CustomerRecommendation:
        validate_as_of(as_of)
        context = await self.memory.recall(customer_ref, as_of, destination=destination)
        destination_code = context.current_situation.destination
        catalogue = await self.catalogue.list_roaming(country_code=destination_code)
        return build_recommendation(context, catalogue)
