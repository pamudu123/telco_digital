"""Read-only Copilot over structured decisions. It does not invent facts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Literal

import requests
from pydantic import BaseModel, ConfigDict

from telco_digital.config import Settings
from telco_digital.decisioning import CustomerDecision, DecisionEngine
from telco_digital.intelligence.features.service import validate_as_of

COPILOT_SET_VERSION = "customer-copilot-v1"
PLAN_TOKEN = re.compile(r"\b(?:ROAM|PLAN|POC)_[A-Z0-9]+\b")
AnswerSource = Literal["deterministic_fallback", "openrouter_glm"]


class CopilotAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: AnswerSource
    copilot_set_version: str = COPILOT_SET_VERSION
    customer_ref: str
    as_of: datetime
    question: str
    answer: str
    used_facts: tuple[str, ...]
    unknowns: tuple[str, ...]
    model: str | None = None
    fallback_reason: str | None = None


def context_pack(decision: CustomerDecision) -> dict[str, object]:
    allowed_plans = [decision.target_plan_code, *decision.explanation.alternatives]
    return {
        "customer_ref": decision.customer_ref,
        "action": decision.action,
        "target_plan_code": decision.target_plan_code,
        "reason_codes": list(decision.reason_codes),
        "what": decision.explanation.what,
        "why": decision.explanation.why,
        "evidence": decision.explanation.evidence,
        "alternatives": list(decision.explanation.alternatives),
        "unknowns": list(decision.unknowns),
        "churn_risk_band": decision.churn_risk_band,
        "traits": list(decision.traits),
        "allowed_plan_codes": [code for code in allowed_plans if code],
    }


def render_fallback(question: str, decision: CustomerDecision) -> str:
    evidence = decision.explanation.evidence
    alternatives = ", ".join(decision.explanation.alternatives) or "none"
    return (
        f"Question: {question.strip() or 'Why is this customer receiving this recommendation?'}\n"
        f"{decision.explanation.what} {decision.explanation.why} "
        f"Reason codes: {', '.join(decision.reason_codes)}. "
        f"Historical plan: {evidence.get('historical_plan') or 'unknown'}. "
        f"Historical usage: {evidence.get('historical_usage_gb') or 'unknown'} GB. "
        f"Catalogue alternatives: {alternatives}. "
        f"Churn band: {decision.churn_risk_band or 'unknown'}. "
        "Trip duration is unknown unless a later trip has already ended. "
        "No plan is invented outside the catalogue, and a churn score is not a discount."
    )


def used_facts(decision: CustomerDecision) -> tuple[str, ...]:
    facts = [
        f"action={decision.action}",
        f"target={decision.target_plan_code or 'none'}",
        *decision.reason_codes,
    ]
    if decision.explanation.evidence.get("historical_plan"):
        facts.append(f"historical_plan={decision.explanation.evidence['historical_plan']}")
    if decision.explanation.evidence.get("historical_usage_gb") is not None:
        facts.append(f"historical_usage_gb={decision.explanation.evidence['historical_usage_gb']}")
    return tuple(facts)


def _allowed_plans(decision: CustomerDecision) -> set[str]:
    return {
        code for code in (decision.target_plan_code, *decision.explanation.alternatives) if code
    }


def is_ungrounded(answer: str, decision: CustomerDecision) -> bool:
    allowed = _allowed_plans(decision)
    mentioned = set(PLAN_TOKEN.findall(answer.upper()))
    extra = mentioned - allowed
    if extra:
        return True
    lowered = answer.lower()
    if "fake_plan" in lowered or "fake plan" in lowered:
        return True
    if "20%" in answer and "not" not in lowered:
        return True
    return False


def _openrouter_complete(settings: Settings, question: str, pack: dict[str, object]) -> str:
    key = (settings.openrouter_api_key or "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a read-only telco intelligence copilot. "
                        "Answer only from the supplied JSON context. "
                        "If a fact is missing, say it is unknown. "
                        "Do not invent plan codes, discounts, or destinations."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"question": question, "context": pack}),
                },
            ],
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload["choices"][0]["message"]["content"]).strip()


def answer_from_decision(
    question: str,
    decision: CustomerDecision,
    settings: Settings | None = None,
) -> CopilotAnswer:
    fallback = render_fallback(question, decision)
    facts = used_facts(decision)
    if settings is None or not (settings.openrouter_api_key or "").strip():
        return CopilotAnswer(
            source="deterministic_fallback",
            customer_ref=decision.customer_ref,
            as_of=decision.as_of,
            question=question,
            answer=fallback,
            used_facts=facts,
            unknowns=decision.unknowns,
            fallback_reason="OpenRouter is not configured.",
        )
    try:
        generated = _openrouter_complete(settings, question, context_pack(decision))
    except Exception as exc:
        return CopilotAnswer(
            source="deterministic_fallback",
            customer_ref=decision.customer_ref,
            as_of=decision.as_of,
            question=question,
            answer=fallback,
            used_facts=facts,
            unknowns=decision.unknowns,
            model=settings.openrouter_model,
            fallback_reason=f"OpenRouter call failed: {exc}",
        )
    if not generated or is_ungrounded(generated, decision):
        return CopilotAnswer(
            source="deterministic_fallback",
            customer_ref=decision.customer_ref,
            as_of=decision.as_of,
            question=question,
            answer=fallback,
            used_facts=facts,
            unknowns=decision.unknowns,
            model=settings.openrouter_model,
            fallback_reason="Model output was empty or mentioned facts outside the context pack.",
        )
    return CopilotAnswer(
        source="openrouter_glm",
        customer_ref=decision.customer_ref,
        as_of=decision.as_of,
        question=question,
        answer=generated,
        used_facts=facts,
        unknowns=decision.unknowns,
        model=settings.openrouter_model,
    )


class CopilotService:
    def __init__(self, engine: DecisionEngine, settings: Settings | None = None) -> None:
        self.engine = engine
        self.settings = settings

    async def answer(
        self,
        question: str,
        customer_ref: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CopilotAnswer:
        validate_as_of(as_of)
        decision = await self.engine.evaluate(customer_ref, as_of, destination=destination)
        return answer_from_decision(question, decision, self.settings)
