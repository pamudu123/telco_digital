from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.config import Settings
from telco_digital.copilot import (
    CopilotService,
    answer_from_decision,
    is_ungrounded,
    render_fallback,
)
from telco_digital.decisioning import decide
from telco_digital.intelligence.behaviour import BehaviourTrait, CustomerBehaviour
from telco_digital.intelligence.churn import CustomerChurn
from telco_digital.intelligence.recommendations import (
    CustomerRecommendation,
    DecisionMode,
    RankedOffer,
)

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")
CUSTOMER_ID = uuid4()
QUESTION = "Why is U001 receiving this recommendation?"


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


def _u001_decision():
    offer = _offer()
    recs = CustomerRecommendation(
        customer_id=CUSTOMER_ID,
        customer_ref="U001",
        as_of=AS_OF,
        computed_at=AS_OF,
        mode=DecisionMode.SCENARIO_BASED,
        primary=offer,
        ranked=(offer, _offer("ROAM_5", 0.2), _offer("ROAM_30", 0.3)),
        evidence={
            "historical_plan": "ROAM_15",
            "historical_usage_gb": 11.4,
            "duration_known": False,
        },
        unknowns=("Trip duration is unknown; offers are ranked as duration scenarios.",),
    )
    behaviour = CustomerBehaviour(
        customer_id=CUSTOMER_ID,
        customer_ref="U001",
        as_of=AS_OF,
        computed_at=AS_OF,
        traits=(BehaviourTrait(trait="FREQUENT_TRAVELLER", confidence=0.8, evidence={}),),
    )
    churn = CustomerChurn(
        customer_id=CUSTOMER_ID,
        customer_ref="U001",
        as_of=AS_OF,
        computed_at=AS_OF,
        model_version="churn-lr-v1",
        model_type="logistic_regression",
        probability=0.05,
        risk_band="LOW",
        drivers=(),
        feature_snapshot={},
    )
    return decide(recs, behaviour, churn)


def test_fallback_names_roam_15_and_duration_unknown() -> None:
    decision = _u001_decision()
    text = render_fallback(QUESTION, decision)
    assert "ROAM_15" in text
    assert "duration" in text.lower()
    assert "unknown" in text.lower()
    assert "FAKE_PLAN" not in text
    assert "20%" not in text


def test_ungrounded_fake_plan_is_rejected() -> None:
    decision = _u001_decision()
    assert is_ungrounded("Present FAKE_PLAN at 20% off", decision) is True
    assert is_ungrounded("Present catalogue offer ROAM_15.", decision) is False


def test_missing_key_uses_deterministic_fallback() -> None:
    decision = _u001_decision()
    answer = answer_from_decision(QUESTION, decision, Settings(openrouter_api_key=None))
    assert answer.source == "deterministic_fallback"
    assert "ROAM_15" in answer.answer
    assert "duration" in answer.answer.lower()
    assert "FAKE_PLAN" not in answer.answer


def test_ungrounded_model_text_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    decision = _u001_decision()

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "Give FAKE_PLAN and a 20% discount."}}]}

    monkeypatch.setattr(
        "telco_digital.copilot.service.requests.post",
        lambda *args, **kwargs: Response(),
    )
    answer = answer_from_decision(
        QUESTION,
        decision,
        Settings(openrouter_api_key="test-key", openrouter_model="z-ai/glm-4.5-flash"),
    )
    assert answer.source == "deterministic_fallback"
    assert "ROAM_15" in answer.answer
    assert "FAKE_PLAN" not in answer.answer
    assert answer.fallback_reason is not None


def test_grounded_model_text_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    decision = _u001_decision()

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "ROAM_15 is ranked from the March episode. Duration is unknown."
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr(
        "telco_digital.copilot.service.requests.post",
        lambda *args, **kwargs: Response(),
    )
    answer = answer_from_decision(
        QUESTION,
        decision,
        Settings(openrouter_api_key="test-key"),
    )
    assert answer.source == "openrouter_glm"
    assert "ROAM_15" in answer.answer


@pytest.mark.asyncio
async def test_copilot_service_uses_engine() -> None:
    decision = _u001_decision()

    class Engine:
        async def evaluate(self, customer_ref, as_of, *, destination=None):
            return decision

    answer = await CopilotService(Engine(), Settings()).answer(
        QUESTION, "U001", AS_OF, destination="SG"
    )
    assert answer.source == "deterministic_fallback"
    assert answer.customer_ref == "U001"
    assert "PRESENT_OFFER" in " ".join(answer.used_facts)
