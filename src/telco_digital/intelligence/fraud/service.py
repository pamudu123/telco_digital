"""Point-in-time graph fraud scores.

Transaction-only risk is computed from PostgreSQL money facts. Graph risk is
computed from the rebuildable Neo4j projection plus deterministic rules.
Predictions are derived and are never a source of truth.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.features.service import validate_as_of
from telco_digital.intelligence.fraud.features import (
    GRAPH_FEATURE_SET_VERSION,
    KNOWN_FRAUD_CUSTOMER_REFS,
    PREDICTION_SET_VERSION,
    SCORER_VERSION,
    TRANSACTION_FEATURE_SET_VERSION,
    GraphFraudFeatures,
    TransactionRiskFeatures,
    features_as_snapshot,
    graph_unavailable,
)
from telco_digital.intelligence.fraud.rules import FraudRule
from telco_digital.intelligence.fraud.scorer import RiskBand, score_parts


class FraudDriver(BaseModel):
    model_config = ConfigDict(frozen=True)

    feature: str
    value: float | int | None
    contribution: str


class CustomerFraud(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    prediction_set_version: str = PREDICTION_SET_VERSION
    scorer_version: str = SCORER_VERSION
    transaction_feature_set_version: str = TRANSACTION_FEATURE_SET_VERSION
    graph_feature_set_version: str = GRAPH_FEATURE_SET_VERSION
    transaction_risk: float
    graph_risk: float
    combined_risk: float
    risk_band: RiskBand
    graph_available: bool
    in_known_fraud_seed: bool
    rules: tuple[FraudRule, ...]
    drivers: tuple[FraudDriver, ...]
    feature_snapshot: dict
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "PostgreSQL outgoing money transactions",
        "Neo4j rebuildable projection",
        "Deterministic fraud rules; scores are derived and not persisted",
    )


class TransactionRiskQueries(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> TransactionRiskFeatures: ...


class GraphFraudQueries(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFraudFeatures: ...


def _drivers(
    transaction_risk: float,
    graph_risk: float,
    rules: tuple[FraudRule, ...],
    graph: GraphFraudFeatures,
) -> tuple[FraudDriver, ...]:
    fired = [rule for rule in rules if rule.fired]
    items = [
        FraudDriver(
            feature="transaction_risk",
            value=transaction_risk,
            contribution="outgoing velocity, transfer ratio and spend without graph walks",
        ),
        FraudDriver(
            feature="graph_risk",
            value=graph_risk if graph.available else None,
            contribution=(
                "shared devices, wallet funnel, proximity to seeded fraud and cluster density"
                if graph.available
                else "graph features unavailable"
            ),
        ),
    ]
    for rule in fired:
        items.append(
            FraudDriver(
                feature=rule.code,
                value=rule.boost,
                contribution=str(rule.evidence.get("note") or rule.severity),
            )
        )
    return tuple(items)


def score_fraud(
    transaction: TransactionRiskFeatures,
    graph: GraphFraudFeatures,
) -> CustomerFraud:
    validate_as_of(transaction.as_of)
    transaction_risk, graph_risk, combined, band, rules = score_parts(transaction, graph)
    unknowns = list(transaction.unknowns) + list(graph.unknowns)
    if not graph.available:
        unknowns.append(
            "Combined risk uses transaction-only evidence while graph features are unavailable."
        )
    return CustomerFraud(
        customer_id=transaction.customer_id,
        customer_ref=transaction.customer_ref,
        as_of=transaction.as_of,
        computed_at=datetime.now(tz=UTC),
        transaction_risk=transaction_risk,
        graph_risk=graph_risk,
        combined_risk=combined,
        risk_band=band,
        graph_available=graph.available,
        in_known_fraud_seed=transaction.customer_ref in KNOWN_FRAUD_CUSTOMER_REFS,
        rules=rules,
        drivers=_drivers(transaction_risk, graph_risk, rules, graph),
        feature_snapshot=features_as_snapshot(transaction, graph),
        unknowns=tuple(dict.fromkeys(unknowns)),
    )


class FraudService:
    def __init__(
        self,
        transactions: TransactionRiskQueries,
        graph: GraphFraudQueries,
    ) -> None:
        self.transactions = transactions
        self.graph = graph

    async def evaluate(self, customer_ref: str, as_of: datetime) -> CustomerFraud:
        validate_as_of(as_of)
        transaction = await self.transactions.calculate(customer_ref, as_of)
        try:
            graph = await self.graph.calculate(customer_ref, as_of)
        except Exception:
            graph = graph_unavailable(
                "Neo4j graph fraud features are unavailable; graph risk is not assumed to be zero."
            )
        return score_fraud(transaction, graph)
