from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.intelligence.fraud import (
    KNOWN_FRAUD_CUSTOMER_REFS,
    PREDICTION_SET_VERSION,
    SCORER_VERSION,
    FraudService,
    GraphFraudFeatures,
    TransactionRiskFeatures,
    score_fraud,
)

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


def _transaction(ref: str, **values) -> TransactionRiskFeatures:
    return TransactionRiskFeatures(
        customer_id=uuid4(),
        customer_ref=ref,
        as_of=AS_OF,
        **values,
    )


def _graph(**values) -> GraphFraudFeatures:
    return GraphFraudFeatures(available=True, **values)


def test_u009_like_cluster_is_high_and_graph_exceeds_transaction() -> None:
    document = score_fraud(
        _transaction(
            "U009",
            transaction_count_90d=2,
            transfer_count_90d=2,
            spend_90d=1600,
            unique_devices_90d=1,
            account_age_days=400,
        ),
        _graph(
            incoming_transfer_counterparty_count=10,
            outgoing_transfer_counterparty_count=1,
            shared_wallet_count=11,
            suspicious_neighbor_count=10,
            distance_to_known_fraud=0,
            connected_component_size=12,
            transaction_cluster_density=0.4,
            neighbor_refs=("BG0095", "U006"),
        ),
    )
    assert document.risk_band == "HIGH"
    assert document.transaction_risk < document.graph_risk
    assert document.transaction_risk < 0.45
    assert document.graph_risk >= 0.80
    assert document.in_known_fraud_seed
    fired = {rule.code for rule in document.rules if rule.fired}
    assert "WALLET_FUNNEL" in fired
    assert "KNOWN_FRAUD_WITHIN_2_HOPS" in fired
    assert document.prediction_set_version == PREDICTION_SET_VERSION
    assert document.scorer_version == SCORER_VERSION
    assert document.source == "derived_live"


def test_u003_like_activity_stays_low() -> None:
    document = score_fraud(
        _transaction(
            "U003",
            transaction_count_90d=2,
            transfer_count_90d=0,
            merchant_payment_count_90d=2,
            spend_90d=1600,
            unique_merchants_90d=2,
            unique_devices_90d=1,
            account_age_days=800,
        ),
        _graph(connected_component_size=1),
    )
    assert document.risk_band == "LOW"
    assert document.transaction_risk < 0.20
    assert document.graph_risk == 0.0
    assert not document.in_known_fraud_seed
    assert not any(rule.fired for rule in document.rules)


def test_shared_device_without_wallet_path_does_not_mark_known_fraud_hops() -> None:
    document = score_fraud(
        _transaction("U001", account_age_days=500),
        _graph(shared_device_customer_count=1, neighbor_refs=("U005",)),
    )
    fired = {rule.code: rule for rule in document.rules if rule.fired}
    assert "SHARED_DEVICE" in fired
    assert "KNOWN_FRAUD_WITHIN_2_HOPS" not in fired
    assert document.risk_band == "LOW"


def test_u005_seed_membership_raises_graph_above_empty_transactions() -> None:
    document = score_fraud(
        _transaction("U005", account_age_days=50),
        _graph(
            shared_device_customer_count=1,
            distance_to_known_fraud=0,
            neighbor_refs=("U001",),
        ),
    )
    assert "U005" in KNOWN_FRAUD_CUSTOMER_REFS
    assert document.transaction_risk == 0.0
    assert document.graph_risk > document.transaction_risk
    fired = {rule.code for rule in document.rules if rule.fired}
    assert "SHARED_DEVICE" in fired
    assert "KNOWN_FRAUD_WITHIN_2_HOPS" in fired


def test_unavailable_graph_does_not_assume_zero_graph_risk() -> None:
    document = score_fraud(
        _transaction("U009", transaction_count_90d=2, transfer_count_90d=2, spend_90d=1600),
        GraphFraudFeatures(
            available=False,
            unknowns=(
                "Neo4j graph fraud features are unavailable; graph risk is not assumed to be zero.",
            ),
        ),
    )
    assert document.graph_available is False
    assert document.combined_risk == document.transaction_risk
    assert any("unavailable" in item.lower() for item in document.unknowns)


def test_naive_as_of_is_rejected() -> None:
    features = _transaction("U009")
    features = features.model_copy(update={"as_of": datetime(2026, 8, 21)})
    with pytest.raises(ValueError, match="timezone-aware"):
        score_fraud(features, _graph())


@pytest.mark.asyncio
async def test_service_scores_from_injected_queries() -> None:
    transaction = _transaction(
        "U009",
        transaction_count_90d=2,
        transfer_count_90d=2,
        spend_90d=1600,
        unique_devices_90d=1,
    )
    graph = _graph(
        incoming_transfer_counterparty_count=10,
        suspicious_neighbor_count=10,
        distance_to_known_fraud=0,
        connected_component_size=12,
        transaction_cluster_density=0.4,
    )

    class Transactions:
        async def calculate(self, customer_ref: str, as_of: datetime):
            return transaction

    class Graph:
        async def calculate(self, customer_ref: str, as_of: datetime):
            return graph

    result = await FraudService(Transactions(), Graph()).evaluate("U009", AS_OF)
    assert result.customer_ref == "U009"
    assert result.risk_band == "HIGH"
