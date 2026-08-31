"""Deterministic graph-fraud rules (Milestone 8)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.fraud.features import GraphFraudFeatures, TransactionRiskFeatures

RuleSeverity = Literal["low", "medium", "high"]
EvidenceValue = int | float | str | None

RULE_BOOSTS: dict[str, float] = {
    "SHARED_DEVICE": 0.08,
    "KNOWN_FRAUD_WITHIN_2_HOPS": 0.15,
    "WALLET_FUNNEL": 0.15,
    "CIRCULAR_TRANSFERS": 0.15,
    "ABNORMAL_CREATION": 0.10,
    "ABNORMAL_TRANSACTION_VELOCITY": 0.10,
}


class FraudRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    fired: bool
    severity: RuleSeverity
    boost: float
    evidence: dict[str, EvidenceValue]


def evaluate_rules(
    transaction: TransactionRiskFeatures,
    graph: GraphFraudFeatures,
) -> tuple[FraudRule, ...]:
    """Return every evaluated rule, including those that did not fire."""

    shared = graph.shared_device_customer_count
    distance = graph.distance_to_known_fraud
    incoming = graph.incoming_transfer_counterparty_count
    circular = graph.circular_transfer_count
    age = transaction.account_age_days
    count = transaction.transaction_count_90d

    checks: tuple[tuple[str, RuleSeverity, bool, dict[str, EvidenceValue]], ...] = (
        (
            "SHARED_DEVICE",
            "low",
            graph.available and shared >= 1,
            {
                "shared_device_customer_count": shared,
                "note": "Time-bounded USES overlap on the Neo4j projection.",
            },
        ),
        (
            "KNOWN_FRAUD_WITHIN_2_HOPS",
            "high",
            graph.available and distance is not None and distance <= 2,
            {
                "distance_to_known_fraud": distance,
                "note": "Wallet/transfer hops only; device sharing is a separate rule.",
            },
        ),
        (
            "WALLET_FUNNEL",
            "high",
            graph.available and incoming >= 5,
            {
                "incoming_transfer_counterparty_count": incoming,
                "note": "Distinct counterparties that transferred into this wallet.",
            },
        ),
        (
            "CIRCULAR_TRANSFERS",
            "high",
            graph.available and circular >= 1,
            {
                "circular_transfer_count": circular,
                "note": "A-to-B and B-to-A transfers in the 90-day window.",
            },
        ),
        (
            "ABNORMAL_CREATION",
            "medium",
            age is not None and age <= 45 and count >= 4,
            {
                "account_age_days": age,
                "transaction_count_90d": count,
            },
        ),
        (
            "ABNORMAL_TRANSACTION_VELOCITY",
            "medium",
            count >= 8,
            {"transaction_count_90d": count},
        ),
    )
    rules: list[FraudRule] = []
    for code, severity, fired, evidence in checks:
        boost = RULE_BOOSTS[code] if fired else 0.0
        rules.append(
            FraudRule(
                code=code,
                fired=fired,
                severity=severity,
                boost=boost,
                evidence=evidence,
            )
        )
    return tuple(rules)


class FraudRuleService:
    def evaluate(
        self,
        transaction: TransactionRiskFeatures,
        graph: GraphFraudFeatures,
    ) -> tuple[FraudRule, ...]:
        return evaluate_rules(transaction, graph)
