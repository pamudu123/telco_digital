"""Synthetic golden fixtures for the capability-07 notebook."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from telco_digital.intelligence.fraud import GraphFraudFeatures, TransactionRiskFeatures

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


def transaction(ref: str, **values) -> TransactionRiskFeatures:
    return TransactionRiskFeatures(
        customer_id=uuid4(),
        customer_ref=ref,
        as_of=AS_OF,
        **values,
    )


def graph(**values) -> GraphFraudFeatures:
    return GraphFraudFeatures(available=True, **values)


GOLDEN = {
    "U009": (
        transaction(
            "U009",
            transaction_count_90d=2,
            transfer_count_90d=2,
            spend_90d=1600,
            unique_devices_90d=1,
            account_age_days=400,
        ),
        graph(
            incoming_transfer_counterparty_count=10,
            outgoing_transfer_counterparty_count=1,
            shared_wallet_count=11,
            suspicious_neighbor_count=10,
            distance_to_known_fraud=0,
            connected_component_size=12,
            transaction_cluster_density=0.4,
            neighbor_refs=("BG0095", "U006"),
        ),
    ),
    "U005": (
        transaction("U005", account_age_days=50),
        graph(
            shared_device_customer_count=1,
            distance_to_known_fraud=0,
            neighbor_refs=("U001",),
        ),
    ),
    "U001": (
        transaction("U001", account_age_days=500),
        graph(shared_device_customer_count=1, neighbor_refs=("U005",)),
    ),
    "U003": (
        transaction(
            "U003",
            transaction_count_90d=2,
            transfer_count_90d=0,
            merchant_payment_count_90d=2,
            spend_90d=1600,
            unique_merchants_90d=2,
            unique_devices_90d=1,
            account_age_days=800,
        ),
        graph(connected_component_size=1),
    ),
}
