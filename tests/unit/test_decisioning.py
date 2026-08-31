from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.decisioning import (
    DECISION_SET_VERSION,
    DecisionAction,
    DecisionEngine,
    decide,
)
from telco_digital.intelligence.behaviour import BehaviourTrait, CustomerBehaviour
from telco_digital.intelligence.churn import CustomerChurn
from telco_digital.intelligence.recommendations import (
    CustomerRecommendation,
    DecisionMode,
    RankedOffer,
)

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")
CUSTOMER_ID = uuid4()


def _offer(code: str = "ROAM_15", score: float = 0.9) -> RankedOffer:
    return RankedOffer(
        plan_code=code,
        plan_name=code,
        plan_type="ROAMING",
        data_mb=15360,
        validity_days=15,
        price=350,
        currency="LKR",
        country_code="SG",
        score=score,
        confidence=0.82,
        scenario_label="4–7 days",
        scenario_days=(4, 7),
        reasons=("Present in the active catalogue",),
    )


def _recs(
    ref: str,
    *,
    mode: DecisionMode,
    primary: RankedOffer | None,
    ranked: tuple[RankedOffer, ...] = (),
    historical_plan: str | None = "ROAM_15",
) -> CustomerRecommendation:
    return CustomerRecommendation(
        customer_id=CUSTOMER_ID,
        customer_ref=ref,
        as_of=AS_OF,
        computed_at=AS_OF,
        mode=mode,
        primary=primary,
        ranked=ranked,
        evidence={
            "historical_plan": historical_plan,
            "historical_usage_gb": 11.4,
            "duration_known": False,
        },
        unknowns=("Trip duration is unknown; offers are ranked as duration scenarios.",),
    )


def _behaviour(ref: str, *traits: str) -> CustomerBehaviour:
    return CustomerBehaviour(
        customer_id=CUSTOMER_ID,
        customer_ref=ref,
        as_of=AS_OF,
        computed_at=AS_OF,
        traits=tuple(
            BehaviourTrait(trait=name, confidence=0.8, evidence={"test": True}) for name in traits
        ),
    )


def _churn(ref: str, band: str, **snapshot: float) -> CustomerChurn:
    return CustomerChurn(
        customer_id=CUSTOMER_ID,
        customer_ref=ref,
        as_of=AS_OF,
        computed_at=AS_OF,
        model_version="churn-lr-v1",
        model_type="logistic_regression",
        probability=0.99 if band == "HIGH" else 0.05,
        risk_band=band,  # type: ignore[arg-type]
        drivers=(),
        feature_snapshot=snapshot,
    )


def test_u001_presents_roam_15_from_catalogue() -> None:
    offer = _offer()
    document = decide(
        _recs(
            "U001",
            mode=DecisionMode.SCENARIO_BASED,
            primary=offer,
            ranked=(offer, _offer("ROAM_30", 0.3), _offer("ROAM_5", 0.1)),
        ),
        _behaviour("U001", "FREQUENT_TRAVELLER"),
        _churn("U001", "LOW"),
    )
    assert document.action == DecisionAction.PRESENT_OFFER
    assert document.target_plan_code == "ROAM_15"
    assert "HISTORICAL_EPISODE" in document.reason_codes
    assert "CATALOGUE_MATCH" in document.reason_codes
    assert "DURATION_UNKNOWN" in document.reason_codes
    assert "ROAM_30" in document.explanation.alternatives
    assert document.decision_set_version == DECISION_SET_VERSION
    assert "discount" not in document.explanation.what.lower()


def test_u004_high_churn_is_support_not_discount() -> None:
    document = decide(
        _recs("U004", mode=DecisionMode.ASK_FOR_INFORMATION, primary=None),
        _behaviour("U004", "DECLINING_ENGAGEMENT"),
        _churn("U004", "HIGH", complaint_count_90d=1, open_ticket_count=2),
    )
    assert document.action == DecisionAction.SUPPORT_FOLLOW_UP
    assert document.target_plan_code is None
    assert document.reason_codes == ("CHURN_HIGH", "NETWORK_OR_COMPLAINT", "NO_AUTO_DISCOUNT")
    text = f"{document.explanation.what} {document.explanation.why}".lower()
    assert "discount" in text
    assert "not" in text
    assert "20%" not in text
    assert "FAKE_PLAN" not in text


def test_high_churn_blocks_upsell_even_when_an_offer_exists() -> None:
    offer = _offer()
    document = decide(
        _recs("U004", mode=DecisionMode.SCENARIO_BASED, primary=offer, ranked=(offer,)),
        _behaviour("U004", "DECLINING_ENGAGEMENT"),
        _churn("U004", "HIGH", open_ticket_count=1),
    )
    assert document.action == DecisionAction.SUPPORT_FOLLOW_UP
    assert document.target_plan_code is None


def test_u002_price_sensitive_does_not_invent_an_offer() -> None:
    document = decide(
        _recs("U002", mode=DecisionMode.ASK_FOR_INFORMATION, primary=None, historical_plan=None),
        _behaviour("U002", "PRICE_SENSITIVE"),
        _churn("U002", "LOW"),
    )
    assert document.action == DecisionAction.NO_INVENTED_OFFER
    assert document.target_plan_code is None
    assert "PRICE_SENSITIVE" in document.reason_codes
    assert "NO_CATALOGUE_TRAVEL_CONTEXT" in document.reason_codes


def test_unknown_destination_requests_information() -> None:
    document = decide(
        _recs("U003", mode=DecisionMode.ASK_FOR_INFORMATION, primary=None, historical_plan=None),
        _behaviour("U003"),
        _churn("U003", "LOW"),
    )
    assert document.action == DecisionAction.REQUEST_INFORMATION
    assert document.reason_codes == ("DESTINATION_UNKNOWN",)


def test_naive_as_of_is_rejected() -> None:
    recs = _recs("U001", mode=DecisionMode.SCENARIO_BASED, primary=_offer())
    recs = recs.model_copy(update={"as_of": datetime(2026, 8, 20, 12)})
    with pytest.raises(ValueError, match="timezone-aware"):
        decide(recs, _behaviour("U001"), _churn("U001", "LOW"))


@pytest.mark.asyncio
async def test_engine_composes_the_three_services() -> None:
    offer = _offer()
    recs = _recs(
        "U001",
        mode=DecisionMode.SCENARIO_BASED,
        primary=offer,
        ranked=(offer,),
    )

    class Recs:
        async def recommend(self, customer_ref, as_of, *, destination=None):
            return recs

    class Behaviour:
        async def evaluate(self, customer_ref, as_of):
            return _behaviour("U001", "FREQUENT_TRAVELLER")

    class Churn:
        async def predict(self, customer_ref, as_of):
            return _churn("U001", "LOW")

    result = await DecisionEngine(Recs(), Behaviour(), Churn()).evaluate(
        "U001", AS_OF, destination="SG"
    )
    assert result.action == DecisionAction.PRESENT_OFFER
    assert result.target_plan_code == "ROAM_15"
