"""Scenario: shared device plus wallet funnel raises graph risk above transactions."""

from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.application.seed import seed_demo_customers
from telco_digital.intelligence.fraud import (
    GraphFraudFeatures,
    TransactionRiskFeatures,
    score_fraud,
)

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


def _transaction(ref: str, customer_id, **values) -> TransactionRiskFeatures:
    return TransactionRiskFeatures(
        customer_id=customer_id,
        customer_ref=ref,
        as_of=AS_OF,
        **values,
    )


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u005_shares_device_and_graph_exceeds_transaction(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    u001 = await uow.customers.get_by_ref("U001")
    u005 = await uow.customers.get_by_ref("U005")
    assert u001 is not None and u005 is not None
    device_001 = await uow.customer_devices.active_at(u001.id, AS_OF)
    device_005 = await uow.customer_devices.active_at(u005.id, AS_OF)
    assert device_001 is not None and device_005 is not None
    assert device_001.device_id == device_005.device_id
    peers = await uow.customer_devices.list_by_device(device_005.device_id)
    peer_ids = {link.customer_id for link in peers}
    assert {u001.id, u005.id} <= peer_ids

    document = score_fraud(
        _transaction(u005.customer_ref, u005.id, account_age_days=50),
        GraphFraudFeatures(
            available=True,
            shared_device_customer_count=len(peer_ids) - 1,
            distance_to_known_fraud=0,
            neighbor_refs=("U001",),
        ),
    )
    assert document.transaction_risk == 0.0
    assert document.graph_risk > document.transaction_risk
    fired = {rule.code for rule in document.rules if rule.fired}
    assert "SHARED_DEVICE" in fired
    assert "KNOWN_FRAUD_WITHIN_2_HOPS" in fired
    assert document.source == "derived_live"


@pytest.mark.scenario
def test_shared_device_and_wallet_funnel_is_high_risk() -> None:
    document = score_fraud(
        _transaction(
            "U009",
            uuid4(),
            transaction_count_90d=2,
            transfer_count_90d=2,
            spend_90d=1600,
            unique_devices_90d=1,
            account_age_days=400,
        ),
        GraphFraudFeatures(
            available=True,
            incoming_transfer_counterparty_count=10,
            outgoing_transfer_counterparty_count=1,
            shared_wallet_count=11,
            merchant_customer_count=0,
            suspicious_neighbor_count=10,
            distance_to_known_fraud=0,
            connected_component_size=12,
            transaction_cluster_density=0.4,
        ),
    )
    assert document.risk_band == "HIGH"
    assert document.transaction_risk < 0.45
    assert document.graph_risk >= 0.80
    fired = {rule.code for rule in document.rules if rule.fired}
    assert {"WALLET_FUNNEL", "KNOWN_FRAUD_WITHIN_2_HOPS"} <= fired


@pytest.mark.scenario
def test_clean_control_customer_stays_low() -> None:
    document = score_fraud(
        _transaction(
            "U003",
            uuid4(),
            transaction_count_90d=2,
            transfer_count_90d=0,
            merchant_payment_count_90d=2,
            spend_90d=1600,
            unique_devices_90d=1,
        ),
        GraphFraudFeatures(available=True, connected_component_size=1),
    )
    assert document.risk_band == "LOW"
    assert not any(rule.fired for rule in document.rules)
