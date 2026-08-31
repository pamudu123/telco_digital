"""Combine transaction-only risk with graph risk.

Scores are derived. A HIGH band is not a write-path block and is not stored
as a Neo4j fact.
"""

from __future__ import annotations

from typing import Literal

from telco_digital.intelligence.fraud.features import (
    GraphFraudFeatures,
    TransactionRiskFeatures,
    graph_risk_components,
    transaction_risk_components,
)
from telco_digital.intelligence.fraud.rules import FraudRule, evaluate_rules

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]

TRANSACTION_WEIGHTS = {
    "velocity": 0.40,
    "transfer_ratio": 0.25,
    "amount_intensity": 0.25,
    "device_spread": 0.10,
}
GRAPH_WEIGHTS = {
    "shared_device": 0.15,
    "proximity": 0.30,
    "suspicious": 0.20,
    "funnel": 0.25,
    "density": 0.05,
    "component": 0.05,
}


def _weighted(components: dict[str, float], weights: dict[str, float]) -> float:
    return round(sum(components[name] * weight for name, weight in weights.items()), 4)


def score_transaction_risk(features: TransactionRiskFeatures) -> float:
    return _weighted(transaction_risk_components(features), TRANSACTION_WEIGHTS)


def score_graph_risk(features: GraphFraudFeatures, rules: tuple[FraudRule, ...]) -> float:
    if not features.available:
        return 0.0
    base = _weighted(graph_risk_components(features), GRAPH_WEIGHTS)
    boost = sum(rule.boost for rule in rules)
    return round(min(1.0, base + boost), 4)


def combine_risk(transaction_risk: float, graph_risk: float, graph_available: bool) -> float:
    if not graph_available:
        return round(transaction_risk, 4)
    return round(0.30 * transaction_risk + 0.70 * graph_risk, 4)


def risk_band(score: float) -> RiskBand:
    if score >= 0.65:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def score_parts(
    transaction: TransactionRiskFeatures,
    graph: GraphFraudFeatures,
) -> tuple[float, float, float, RiskBand, tuple[FraudRule, ...]]:
    rules = evaluate_rules(transaction, graph)
    transaction_risk = score_transaction_risk(transaction)
    graph_risk = score_graph_risk(graph, rules)
    combined = combine_risk(transaction_risk, graph_risk, graph.available)
    return transaction_risk, graph_risk, combined, risk_band(combined), rules
