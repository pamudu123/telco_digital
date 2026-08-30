from telco_digital.application.demo_dataset import DATASET_VERSION, build_dataset


def test_demo_dataset_is_deterministic_and_has_event_parity() -> None:
    first = build_dataset(background_customers=7)
    second = build_dataset(background_customers=7)

    assert first.metrics == second.metrics
    assert first.rows == second.rows
    assert len(first.rows["customers"]) == 12
    assert len(first.rows["activity_events"]) == len(first.rows["outbox_events"])
    assert all(
        event["payload"]["dataset_version"] == DATASET_VERSION
        for event in first.rows["outbox_events"]
    )


def test_demo_dataset_references_only_generated_parent_rows() -> None:
    bundle = build_dataset(background_customers=10)
    customer_ids = {row["id"] for row in bundle.rows["customers"]}
    account_ids = {row["id"] for row in bundle.rows["accounts"]}
    wallet_ids = {row["id"] for row in bundle.rows["wallets"]}
    plan_ids = {row["id"] for row in bundle.rows["plans"]}

    assert all(row["customer_id"] in customer_ids for row in bundle.rows["recharges"])
    assert all(row["account_id"] in account_ids for row in bundle.rows["recharges"])
    assert all(row["plan_id"] in plan_ids for row in bundle.rows["subscriptions"])
    assert all(row["source_wallet_id"] in wallet_ids for row in bundle.rows["money_transactions"])
    assert all(
        row["destination_wallet_id"] is None or row["destination_wallet_id"] in wallet_ids
        for row in bundle.rows["money_transactions"]
    )
