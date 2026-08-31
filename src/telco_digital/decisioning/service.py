"""Next-best action from structured intelligence. Predictions are not discounts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.behaviour import CustomerBehaviour
from telco_digital.intelligence.churn import CustomerChurn
from telco_digital.intelligence.features.service import validate_as_of
from telco_digital.intelligence.recommendations import (
    CustomerRecommendation,
    DecisionMode,
    RankedOffer,
)

DECISION_SET_VERSION = "customer-decision-v1"


class DecisionAction(StrEnum):
    PRESENT_OFFER = "PRESENT_OFFER"
    SUPPORT_FOLLOW_UP = "SUPPORT_FOLLOW_UP"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    NO_INVENTED_OFFER = "NO_INVENTED_OFFER"


class DecisionExplanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    what: str
    why: str
    evidence: dict[str, str | float | int | None]
    confidence: float
    unknowns: tuple[str, ...]
    alternatives: tuple[str, ...]


class CustomerDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    decision_set_version: str = DECISION_SET_VERSION
    action: DecisionAction
    target_plan_code: str | None = None
    reason_codes: tuple[str, ...]
    confidence: float
    explanation: DecisionExplanation
    recommendation_mode: str | None = None
    churn_risk_band: str | None = None
    traits: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "Behaviour traits, churn score and catalogue recommendations",
        "Predictions do not become discounts by themselves",
        "Decisions are derived and not persisted",
        "Fraud, forecast and digital-twin inputs are unknown on this branch",
    )


class RecommendationEvaluator(Protocol):
    async def recommend(
        self, customer_ref: str, as_of: datetime, *, destination: str | None = None
    ) -> CustomerRecommendation: ...


class BehaviourEvaluator(Protocol):
    async def evaluate(self, customer_ref: str, as_of: datetime) -> CustomerBehaviour: ...


class ChurnPredictor(Protocol):
    async def predict(self, customer_ref: str, as_of: datetime) -> CustomerChurn: ...


def _traits(behaviour: CustomerBehaviour) -> set[str]:
    return {item.trait for item in behaviour.traits}


def _snapshot_number(churn: CustomerChurn, key: str) -> float:
    raw = churn.feature_snapshot.get(key)
    if raw is None:
        return 0.0
    return float(raw)


def _needs_support(behaviour: CustomerBehaviour, churn: CustomerChurn) -> bool:
    traits = _traits(behaviour)
    service_pressure = (
        _snapshot_number(churn, "complaint_count_90d") >= 1
        or _snapshot_number(churn, "open_ticket_count") >= 1
    )
    return churn.risk_band == "HIGH" and ("DECLINING_ENGAGEMENT" in traits or service_pressure)


def _shared_unknowns(
    recommendation: CustomerRecommendation,
    *,
    extra: tuple[str, ...] = (),
) -> tuple[str, ...]:
    items = [
        *recommendation.unknowns,
        "Graph fraud scoring is unknown (capability 07 is not on this branch).",
        "Retailer forecast is unknown (capability 08 is not on this branch).",
        "A computed digital twin is unknown (capability 09 is not on this branch).",
        *extra,
    ]
    return tuple(dict.fromkeys(items))


def _alternatives(ranked: tuple[RankedOffer, ...], chosen: str | None) -> tuple[str, ...]:
    return tuple(item.plan_code for item in ranked if item.plan_code != chosen)


def decide(
    recommendation: CustomerRecommendation,
    behaviour: CustomerBehaviour,
    churn: CustomerChurn,
) -> CustomerDecision:
    """Choose an NBA from already-built intelligence documents."""

    validate_as_of(recommendation.as_of)
    traits = tuple(sorted(_traits(behaviour)))
    primary = recommendation.primary
    codes: list[str]
    if _needs_support(behaviour, churn):
        action = DecisionAction.SUPPORT_FOLLOW_UP
        codes = ["CHURN_HIGH", "NETWORK_OR_COMPLAINT", "NO_AUTO_DISCOUNT"]
        what = "Follow up on the open service issue. Do not issue a retention discount."
        why = (
            "Churn is HIGH with declining engagement or open network/complaint "
            "tickets. A predicted score is not an offer."
        )
        confidence = 0.84
        target = None
    elif primary is not None and recommendation.mode != DecisionMode.ASK_FOR_INFORMATION:
        action = DecisionAction.PRESENT_OFFER
        codes = ["CATALOGUE_MATCH"]
        if recommendation.evidence.get("historical_plan") == primary.plan_code:
            codes.insert(0, "HISTORICAL_EPISODE")
        if not recommendation.evidence.get("duration_known"):
            codes.append("DURATION_UNKNOWN")
        what = f"Present catalogue offer {primary.plan_code}."
        why = (
            f"Retrieved travel memory ranks {primary.plan_code} "
            f"for the {primary.scenario_label} scenario."
        )
        confidence = primary.confidence
        target = primary.plan_code
    elif recommendation.mode == DecisionMode.ASK_FOR_INFORMATION and "PRICE_SENSITIVE" in traits:
        action = DecisionAction.NO_INVENTED_OFFER
        codes = ["PRICE_SENSITIVE", "NO_CATALOGUE_TRAVEL_CONTEXT"]
        what = "Do not invent a discount or roam plan."
        why = (
            "PRICE_SENSITIVE evidence is present, but there is no travel catalogue "
            "context to rank an offer."
        )
        confidence = 0.72
        target = None
    elif recommendation.mode == DecisionMode.ASK_FOR_INFORMATION:
        action = DecisionAction.REQUEST_INFORMATION
        codes = ["DESTINATION_UNKNOWN"]
        what = "Ask for the travel destination before ranking an offer."
        why = "Catalogue roam plans are destination-scoped and duration is unknown."
        confidence = 0.7
        target = None
    else:
        action = DecisionAction.NO_INVENTED_OFFER
        codes = ["NO_CATALOGUE_MATCH"]
        what = "Do not invent a plan or discount."
        why = "No active catalogue offer is available for this situation."
        confidence = 0.65
        target = None

    unknowns = _shared_unknowns(recommendation)
    explanation = DecisionExplanation(
        what=what,
        why=why,
        evidence={
            "action": action,
            "target_plan_code": target,
            "recommendation_mode": recommendation.mode,
            "historical_plan": recommendation.evidence.get("historical_plan"),
            "historical_usage_gb": recommendation.evidence.get("historical_usage_gb"),
            "churn_risk_band": churn.risk_band,
            "churn_probability": churn.probability,
            "traits": ", ".join(traits) or None,
        },
        confidence=confidence,
        unknowns=unknowns,
        alternatives=_alternatives(recommendation.ranked, target),
    )
    return CustomerDecision(
        customer_id=recommendation.customer_id,
        customer_ref=recommendation.customer_ref,
        as_of=recommendation.as_of,
        computed_at=datetime.now(tz=UTC),
        action=action,
        target_plan_code=target,
        reason_codes=tuple(codes),
        confidence=confidence,
        explanation=explanation,
        recommendation_mode=str(recommendation.mode),
        churn_risk_band=churn.risk_band,
        traits=traits,
        unknowns=unknowns,
    )


class DecisionEngine:
    def __init__(
        self,
        recommendations: RecommendationEvaluator,
        behaviour: BehaviourEvaluator,
        churn: ChurnPredictor,
    ) -> None:
        self.recommendations = recommendations
        self.behaviour = behaviour
        self.churn = churn

    async def evaluate(
        self,
        customer_ref: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CustomerDecision:
        validate_as_of(as_of)
        recommendation = await self.recommendations.recommend(
            customer_ref, as_of, destination=destination
        )
        behaviour = await self.behaviour.evaluate(customer_ref, as_of)
        churn = await self.churn.predict(customer_ref, as_of)
        return decide(recommendation, behaviour, churn)
