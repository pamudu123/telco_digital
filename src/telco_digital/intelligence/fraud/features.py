"""Versioned transaction and graph-fraud feature contracts.

Graph features stay derived. Known-fraud membership is a documented POC seed
list, not an authoritative PostgreSQL or Neo4j fact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.features.service import validate_as_of

TRANSACTION_FEATURE_SET_VERSION = "customer-transaction-risk-v1"
GRAPH_FEATURE_SET_VERSION = "customer-graph-fraud-v1"
PREDICTION_SET_VERSION = "customer-fraud-v1"
SCORER_VERSION = "fraud-rules-v1"

KNOWN_FRAUD_CUSTOMER_REFS: frozenset[str] = frozenset({"U005", "U009"})


class TransactionRiskFeatures(BaseModel):
    """Outgoing money activity visible without walking the graph."""

    model_config = ConfigDict(frozen=True)

    available: bool = True
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    account_age_days: int | None = None
    transaction_count_90d: int = 0
    transfer_count_90d: int = 0
    merchant_payment_count_90d: int = 0
    spend_90d: float = 0.0
    max_amount_90d: float = 0.0
    unique_merchants_90d: int = 0
    unique_devices_90d: int = 0
    unknowns: tuple[str, ...] = ()


class GraphFraudFeatures(BaseModel):
    """Relationship evidence from the rebuildable Neo4j projection."""

    model_config = ConfigDict(frozen=True)

    available: bool
    shared_device_customer_count: int = 0
    shared_wallet_count: int = 0
    incoming_transfer_counterparty_count: int = 0
    outgoing_transfer_counterparty_count: int = 0
    circular_transfer_count: int = 0
    merchant_degree: int = 0
    merchant_customer_count: int = 0
    suspicious_neighbor_count: int = 0
    distance_to_known_fraud: int | None = None
    connected_component_size: int = 1
    transaction_cluster_density: float = 0.0
    neighbor_refs: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


def graph_unavailable(*reasons: str) -> GraphFraudFeatures:
    return GraphFraudFeatures(
        available=False,
        unknowns=reasons
        or ("Neo4j graph fraud features are unavailable; graph risk is not assumed to be zero.",),
    )


def distance_to_known_fraud(
    customer_ref: str,
    wallet_neighbor_refs: list[str] | tuple[str, ...],
    known_refs: frozenset[str] = KNOWN_FRAUD_CUSTOMER_REFS,
) -> int | None:
    """Wallet-path distance only. Device sharing is a separate rule."""

    if customer_ref in known_refs:
        return 0
    if any(ref in known_refs for ref in wallet_neighbor_refs):
        return 1
    return None


def suspicious_neighbors(
    customer_ref: str,
    wallet_neighbor_refs: list[str] | tuple[str, ...],
    incoming_refs: list[str] | tuple[str, ...],
    known_refs: frozenset[str] = KNOWN_FRAUD_CUSTOMER_REFS,
) -> int:
    """Neighbors who are seeded fraud or who transferred into a seeded hub."""

    neighbors = {ref for ref in wallet_neighbor_refs if ref and ref != customer_ref}
    incoming = {ref for ref in incoming_refs if ref and ref != customer_ref}
    flagged = {ref for ref in neighbors if ref in known_refs}
    if customer_ref in known_refs:
        flagged.update(incoming)
    else:
        flagged.update(ref for ref in incoming if ref in known_refs)
        flagged.update(ref for ref in neighbors if ref in known_refs)
    return len(flagged)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def transaction_risk_components(features: TransactionRiskFeatures) -> dict[str, float]:
    validate_as_of(features.as_of)
    count = features.transaction_count_90d
    velocity = _clamp(count / 20)
    transfer_ratio = (features.transfer_count_90d / count) if count else 0.0
    amount = _clamp(features.spend_90d / 20_000)
    devices = _clamp(features.unique_devices_90d / 4)
    return {
        "velocity": round(velocity, 4),
        "transfer_ratio": round(transfer_ratio, 4),
        "amount_intensity": round(amount, 4),
        "device_spread": round(devices, 4),
    }


def graph_risk_components(features: GraphFraudFeatures) -> dict[str, float]:
    distance = features.distance_to_known_fraud
    if distance is None:
        proximity = 0.0
    elif distance == 0:
        proximity = 1.0
    elif distance == 1:
        proximity = 0.85
    elif distance == 2:
        proximity = 0.60
    else:
        proximity = 0.20
    return {
        "shared_device": round(_clamp(features.shared_device_customer_count / 3), 4),
        "proximity": proximity,
        "suspicious": round(_clamp(features.suspicious_neighbor_count / 5), 4),
        "funnel": round(_clamp(features.incoming_transfer_counterparty_count / 8), 4),
        "density": round(_clamp(features.transaction_cluster_density), 4),
        "component": round(_clamp(max(0, features.connected_component_size - 1) / 15), 4),
    }


def features_as_snapshot(
    transaction: TransactionRiskFeatures, graph: GraphFraudFeatures
) -> dict[str, Any]:
    return {
        "transaction_count_90d": transaction.transaction_count_90d,
        "transfer_count_90d": transaction.transfer_count_90d,
        "spend_90d": transaction.spend_90d,
        "unique_devices_90d": transaction.unique_devices_90d,
        "account_age_days": transaction.account_age_days,
        "shared_device_customer_count": graph.shared_device_customer_count,
        "shared_wallet_count": graph.shared_wallet_count,
        "incoming_transfer_counterparty_count": graph.incoming_transfer_counterparty_count,
        "circular_transfer_count": graph.circular_transfer_count,
        "merchant_degree": graph.merchant_degree,
        "merchant_customer_count": graph.merchant_customer_count,
        "suspicious_neighbor_count": graph.suspicious_neighbor_count,
        "distance_to_known_fraud": graph.distance_to_known_fraud,
        "connected_component_size": graph.connected_component_size,
        "transaction_cluster_density": graph.transaction_cluster_density,
    }
