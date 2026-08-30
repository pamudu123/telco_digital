"""Deterministic cross-domain dataset for the shared-intelligence POC."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

DATASET_VERSION = "poc-v1"
DATASET_SEED = 20260831
DATASET_NAMESPACE = UUID("6bc5ab17-91bf-4ac7-aa56-0811f38e9a61")
START_AT = datetime(2025, 9, 1, tzinfo=UTC)
END_AT = datetime(2026, 8, 31, 23, 59, tzinfo=UTC)

GOLDEN_PERSONAS = {
    "U006": "PROMOTION_RESPONSIVE",
    "U007": "UNKNOWN_DURATION_TRAVELLER",
    "U008": "LOYALTY_REACTIVATED",
    "U009": "WALLET_FRAUD_CLUSTER",
    "U010": "RETAIL_LINKED",
}
BACKGROUND_PERSONAS = (
    "FREQUENT_TRAVELLER",
    "PRICE_SENSITIVE",
    "STABLE_HIGH_VALUE",
    "DECLINING_ENGAGEMENT",
    "PROMOTION_RESPONSIVE",
    "WALLET_ACTIVE",
    "STREAMING_HEAVY",
)
SEED_PERSONAS = {
    "U001": "FREQUENT_TRAVELLER",
    "U002": "PRICE_SENSITIVE",
    "U003": "STABLE_HIGH_VALUE",
    "U004": "DECLINING_ENGAGEMENT",
    "U005": "WALLET_FRAUD_CLUSTER",
}
GOLDEN_CUSTOMER_REFS = tuple(f"U{index:03d}" for index in range(1, 11))


def persona_for_ref(customer_ref: str) -> str | None:
    """Map a customer_ref to the documented generator/seed persona code."""
    if customer_ref in SEED_PERSONAS:
        return SEED_PERSONAS[customer_ref]
    if customer_ref in GOLDEN_PERSONAS:
        return GOLDEN_PERSONAS[customer_ref]
    if customer_ref.startswith("BG") and customer_ref[2:].isdigit():
        sequence = int(customer_ref[2:])
        if sequence >= 1:
            return BACKGROUND_PERSONAS[(sequence - 1) % len(BACKGROUND_PERSONAS)]
    return None


def expected_generated_row_count(background_customers: int = 1000) -> int:
    return sum(len(rows) for rows in build_dataset(background_customers).rows.values())


def deterministic_id(kind: str, key: str) -> UUID:
    return uuid5(DATASET_NAMESPACE, f"{DATASET_VERSION}:{kind}:{key}")


@dataclass(frozen=True)
class DatasetBundle:
    rows: dict[str, list[dict[str, Any]]]
    metrics: dict[str, Any]


def build_dataset(background_customers: int = 1000) -> DatasetBundle:
    """Build reproducible rows without touching a database."""
    rng = random.Random(DATASET_SEED)
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    persona_counts: Counter[str] = Counter()
    monthly_usage: Counter[str] = Counter()
    monthly_recharges: Counter[str] = Counter()
    monthly_transactions: Counter[str] = Counter()
    monthly_sales: Counter[str] = Counter()

    _reference_rows(rows)
    customers = list(GOLDEN_PERSONAS.items()) + [
        (f"BG{i:04d}", BACKGROUND_PERSONAS[(i - 1) % len(BACKGROUND_PERSONAS)])
        for i in range(1, background_customers + 1)
    ]

    plan_codes = ("POC_LOCAL_5", "POC_LOCAL_15", "POC_LOCAL_30", "POC_STREAM_20")
    merchant_ids = [deterministic_id("merchant", f"MERCHANT_{i:02d}") for i in range(1, 21)]
    campaign_ids = [deterministic_id("campaign", f"CAMPAIGN_{i:02d}") for i in range(1, 11)]

    for sequence, (customer_ref, persona) in enumerate(customers, start=1):
        persona_counts[persona] += 1
        customer_id = deterministic_id("customer", customer_ref)
        account_id = deterministic_id("account", customer_ref)
        wallet_id = deterministic_id("wallet", customer_ref)
        loyalty_id = deterministic_id("loyalty", customer_ref)
        joined_at = START_AT - timedelta(days=365 + sequence % 900)
        account_type = "POSTPAID" if persona == "STABLE_HIGH_VALUE" else "PREPAID"

        device_key = f"SHARED_{sequence // 50:03d}" if sequence % 50 in (0, 1, 2) else customer_ref
        device_id = deterministic_id("device", device_key)
        if not any(item["id"] == device_id for item in rows["devices"]):
            rows["devices"].append(
                {
                    "id": device_id,
                    "device_ref": f"DEV-{device_key}",
                    "device_type": "SMARTPHONE",
                    "model": ("Pixel", "Galaxy", "iPhone", "Xiaomi")[sequence % 4],
                    "fingerprint": f"fp-{device_key.lower()}",
                    "first_seen_at": joined_at,
                }
            )

        rows["customers"].append(
            {
                "id": customer_id,
                "customer_ref": customer_ref,
                "home_country": "LK",
                "account_type": account_type,
                "status": "ACTIVE",
                "customer_since": joined_at,
                "created_at": joined_at,
                "updated_at": END_AT,
            }
        )
        rows["accounts"].append(
            {
                "id": account_id,
                "customer_id": customer_id,
                "account_ref": f"{customer_ref}-ACC",
                "account_type": account_type,
                "currency": "LKR",
                "status": "ACTIVE",
                "created_at": joined_at,
            }
        )
        rows["customer_devices"].append(
            {
                "id": deterministic_id("customer_device", customer_ref),
                "customer_id": customer_id,
                "device_id": device_id,
                "valid_from": joined_at,
                "valid_to": None,
            }
        )
        rows["wallets"].append(
            {
                "id": wallet_id,
                "wallet_ref": f"W-{customer_ref}",
                "customer_id": customer_id,
                "status": "ACTIVE",
                "created_at": joined_at,
            }
        )
        rows["loyalty_accounts"].append(
            {
                "id": loyalty_id,
                "customer_id": customer_id,
                "joined_at": joined_at + timedelta(days=30),
                "status": "ACTIVE",
            }
        )
        _add_event(rows, "CUSTOMER_CREATED", "customer", customer_id, customer_id, joined_at)

        plan_code = plan_codes[sequence % len(plan_codes)]
        plan_id = deterministic_id("plan", plan_code)
        subscription_at = START_AT + timedelta(days=sequence % 90)
        subscription_id = deterministic_id("subscription", customer_ref)
        subscription_event = _add_event(
            rows, "PLAN_PURCHASED", "subscription", subscription_id, customer_id, subscription_at
        )
        rows["subscriptions"].append(
            {
                "id": subscription_id,
                "customer_id": customer_id,
                "plan_id": plan_id,
                "started_at": subscription_at,
                "ended_at": None,
                "status": "ACTIVE",
                "source_event_id": subscription_event,
            }
        )

        recharge_base = Decimal("1500") if persona == "STABLE_HIGH_VALUE" else Decimal("500")
        if persona == "PRICE_SENSITIVE":
            recharge_base = Decimal("100")
        for month in (0, 3, 6, 9):
            occurred_at = START_AT + timedelta(days=month * 30 + sequence % 20)
            recharge_id = deterministic_id("recharge", f"{customer_ref}:{month}")
            event_id = _add_event(
                rows, "RECHARGE_RECORDED", "recharge", recharge_id, customer_id, occurred_at
            )
            rows["recharges"].append(
                {
                    "id": recharge_id,
                    "customer_id": customer_id,
                    "account_id": account_id,
                    "amount": recharge_base,
                    "currency": "LKR",
                    "occurred_at": occurred_at,
                    "channel": ("APP", "RETAIL", "USSD")[sequence % 3],
                    "source_event_id": event_id,
                }
            )
            rows["balance_ledger"].append(
                {
                    "id": deterministic_id("ledger", f"recharge:{customer_ref}:{month}"),
                    "account_id": account_id,
                    "customer_id": customer_id,
                    "entry_type": "RECHARGE",
                    "amount": recharge_base,
                    "currency": "LKR",
                    "occurred_at": occurred_at,
                    "source_event_id": event_id,
                }
            )
            monthly_recharges[_month(occurred_at)] += 1

        for month in range(0, 12, 2):
            occurred_at = START_AT + timedelta(days=month * 30 + 15 + sequence % 10)
            data_mb = Decimal(2200 if persona == "STREAMING_HEAVY" else 700 + sequence % 900)
            if persona == "DECLINING_ENGAGEMENT":
                data_mb = Decimal(max(100, 1700 - month * 120))
            usage_id = deterministic_id("usage", f"{customer_ref}:{month}")
            event_id = _add_event(
                rows, "USAGE_RECORDED", "usage", usage_id, customer_id, occurred_at
            )
            rows["usage_events"].append(
                {
                    "id": usage_id,
                    "customer_id": customer_id,
                    "occurred_at": occurred_at,
                    "usage_type": "STREAMING" if persona == "STREAMING_HEAVY" else "BROWSING",
                    "data_mb": data_mb,
                    "country_code": "LK",
                    "network_type": "5G" if sequence % 3 == 0 else "4G",
                    "source_event_id": event_id,
                }
            )
            monthly_usage[_month(occurred_at)] += float(data_mb)

        if persona in {"FREQUENT_TRAVELLER", "UNKNOWN_DURATION_TRAVELLER"}:
            travel_at = START_AT + timedelta(days=120 + sequence % 40)
            travel_id = deterministic_id("travel", customer_ref)
            event_id = _add_event(
                rows, "TRAVEL_STARTED", "travel", travel_id, customer_id, travel_at
            )
            rows["travels"].append(
                {
                    "id": travel_id,
                    "customer_id": customer_id,
                    "country_code": "SG",
                    "started_at": travel_at,
                    "ended_at": None
                    if persona == "UNKNOWN_DURATION_TRAVELLER"
                    else travel_at + timedelta(days=6),
                    "source": "POC_SIMULATOR",
                    "start_event_id": event_id,
                    "end_event_id": None,
                }
            )

        if persona == "DECLINING_ENGAGEMENT":
            interaction_at = END_AT - timedelta(days=20 + sequence % 10)
            interaction_id = deterministic_id("interaction", customer_ref)
            event_id = _add_event(
                rows,
                "SERVICE_INTERACTION_RECORDED",
                "service_interaction",
                interaction_id,
                customer_id,
                interaction_at,
            )
            rows["service_interactions"].append(
                {
                    "id": interaction_id,
                    "customer_id": customer_id,
                    "interaction_type": "NETWORK_ISSUE",
                    "occurred_at": interaction_at,
                    "category": "COVERAGE",
                    "severity": "HIGH",
                    "status": "OPEN",
                    "resolved_at": None,
                    "source_event_id": event_id,
                }
            )

        loyalty_at = START_AT + timedelta(days=40 + sequence % 20)
        for entry_type, points, suffix in (("EARN", 250, "earn"), ("REDEEM", -100, "redeem")):
            ledger_id = deterministic_id("loyalty_ledger", f"{customer_ref}:{suffix}")
            event_id = _add_event(
                rows, "LOYALTY_UPDATED", "loyalty", ledger_id, customer_id, loyalty_at
            )
            rows["loyalty_ledger"].append(
                {
                    "id": ledger_id,
                    "loyalty_account_id": loyalty_id,
                    "customer_id": customer_id,
                    "entry_type": entry_type,
                    "points": points,
                    "reward_id": None,
                    "occurred_at": loyalty_at,
                    "source_event_id": event_id,
                }
            )
            loyalty_at += timedelta(days=120)

        campaign_id = campaign_ids[sequence % len(campaign_ids)]
        interaction_type = "CONVERTED" if persona == "PROMOTION_RESPONSIVE" else "OPENED"
        campaign_at = START_AT + timedelta(days=180 + sequence % 60)
        campaign_interaction_id = deterministic_id("campaign_interaction", customer_ref)
        campaign_event = _add_event(
            rows,
            "CAMPAIGN_INTERACTION_RECORDED",
            "campaign",
            campaign_interaction_id,
            customer_id,
            campaign_at,
        )
        rows["campaign_interactions"].append(
            {
                "id": campaign_interaction_id,
                "campaign_id": campaign_id,
                "customer_id": customer_id,
                "interaction_type": interaction_type,
                "occurred_at": campaign_at,
                "source_event_id": campaign_event,
            }
        )

        for transaction_number in range(2):
            occurred_at = START_AT + timedelta(days=210 + transaction_number * 60 + sequence % 25)
            transaction_id = deterministic_id(
                "money_transaction", f"{customer_ref}:{transaction_number}"
            )
            destination_wallet_id = None
            merchant_id = merchant_ids[(sequence + transaction_number) % len(merchant_ids)]
            transaction_type = "MERCHANT_PAYMENT"
            if persona == "WALLET_FRAUD_CLUSTER" or sequence % 100 == 0:
                target_ref = "U009" if customer_ref != "U009" else "U006"
                destination_wallet_id = deterministic_id("wallet", target_ref)
                merchant_id = None
                transaction_type = "TRANSFER"
            event_id = _add_event(
                rows,
                "MONEY_TRANSACTION_RECORDED",
                "money_transaction",
                transaction_id,
                customer_id,
                occurred_at,
            )
            rows["money_transactions"].append(
                {
                    "id": transaction_id,
                    "transaction_ref": f"TX-{customer_ref}-{transaction_number}",
                    "source_wallet_id": wallet_id,
                    "destination_wallet_id": destination_wallet_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer_id,
                    "device_id": device_id,
                    "amount": Decimal(500 + (sequence % 20) * 75),
                    "currency": "LKR",
                    "transaction_type": transaction_type,
                    "country_code": "LK",
                    "occurred_at": occurred_at,
                    "status": "COMPLETED",
                    "source_event_id": event_id,
                }
            )
            monthly_transactions[_month(occurred_at)] += 1

    _sfa_facts(rows, monthly_sales, rng)
    metrics = {
        "dataset_version": DATASET_VERSION,
        "seed": DATASET_SEED,
        "period": {"start": START_AT.isoformat(), "end": END_AT.isoformat()},
        "background_customers": background_customers,
        "new_golden_customers": len(GOLDEN_PERSONAS),
        "expected_existing_golden_customers": 5,
        "row_counts": {name: len(items) for name, items in sorted(rows.items())},
        "persona_counts": dict(sorted(persona_counts.items())),
        "monthly_usage_mb": dict(sorted(monthly_usage.items())),
        "monthly_recharges": dict(sorted(monthly_recharges.items())),
        "monthly_transactions": dict(sorted(monthly_transactions.items())),
        "monthly_sales_amount": dict(sorted(monthly_sales.items())),
    }
    return DatasetBundle(rows=dict(rows), metrics=metrics)


def _reference_rows(rows: dict[str, list[dict[str, Any]]]) -> None:
    plans = (
        ("POC_LOCAL_5", "Local 5GB", "LOCAL", 5120, 30, "400"),
        ("POC_LOCAL_15", "Local 15GB", "LOCAL", 15360, 30, "850"),
        ("POC_LOCAL_30", "Local 30GB", "LOCAL", 30720, 30, "1400"),
        ("POC_STREAM_20", "Streaming 20GB", "ADD_ON", 20480, 30, "950"),
        ("POC_ROAM_3", "Roaming 3GB", "ROAMING", 3072, 3, "1200"),
        ("POC_ROAM_7", "Roaming 7GB", "ROAMING", 7168, 7, "2400"),
        ("POC_ROAM_15", "Roaming 15GB", "ROAMING", 15360, 15, "4200"),
        ("POC_VOICE_500", "Voice 500", "ADD_ON", 0, 30, "300"),
    )
    for code, name, plan_type, data_mb, days, price in plans:
        rows["plans"].append(
            {
                "id": deterministic_id("plan", code),
                "plan_code": code,
                "name": name,
                "plan_type": plan_type,
                "data_mb": data_mb,
                "validity_days": days,
                "price": Decimal(price),
                "currency": "LKR",
                "country_code": "SG" if plan_type == "ROAMING" else None,
                "country_group": None,
                "active": True,
                "created_at": START_AT - timedelta(days=180),
            }
        )
    for index in range(1, 21):
        rows["merchants"].append(
            {
                "id": deterministic_id("merchant", f"MERCHANT_{index:02d}"),
                "merchant_ref": f"M{index:03d}",
                "name": f"POC Merchant {index:02d}",
                "category": ("GROCERY", "UTILITY", "TRANSPORT", "ENTERTAINMENT")[index % 4],
                "country_code": "LK",
                "status": "ACTIVE",
            }
        )
    for index in range(1, 11):
        rows["campaigns"].append(
            {
                "id": deterministic_id("campaign", f"CAMPAIGN_{index:02d}"),
                "campaign_code": f"POC-C{index:02d}",
                "name": f"POC Campaign {index:02d}",
                "category": ("RETENTION", "ROAMING", "LOYALTY", "UPGRADE")[index % 4],
                "target_plan_id": deterministic_id("plan", "POC_LOCAL_15"),
                "starts_at": START_AT + timedelta(days=(index - 1) * 25),
                "ends_at": START_AT + timedelta(days=(index - 1) * 25 + 20),
                "status": "COMPLETED",
            }
        )
    for index in range(1, 6):
        rows["distributors"].append(
            {
                "id": deterministic_id("distributor", str(index)),
                "distributor_ref": f"DIST-{index:02d}",
                "name": f"POC Distributor {index}",
                "region": ("WESTERN", "CENTRAL", "SOUTHERN", "NORTHERN", "EASTERN")[
                    index - 1
                ],
            }
        )
    for index in range(1, 26):
        distributor_id = deterministic_id("distributor", str((index - 1) % 5 + 1))
        rows["retailers"].append(
            {
                "id": deterministic_id("retailer", str(index)),
                "retailer_ref": f"RET-{index:03d}",
                "distributor_id": distributor_id,
                "name": f"POC Retailer {index:02d}",
                "region": ("WESTERN", "CENTRAL", "SOUTHERN", "NORTHERN", "EASTERN")[
                    (index - 1) % 5
                ],
                "latitude": Decimal("6.9271") + Decimal(index) / 1000,
                "longitude": Decimal("79.8612") + Decimal(index) / 1000,
                "status": "ACTIVE",
            }
        )
    for index in range(1, 11):
        rows["sales_agents"].append(
            {
                "id": deterministic_id("sales_agent", str(index)),
                "agent_ref": f"AGENT-{index:03d}",
                "distributor_id": deterministic_id("distributor", str((index - 1) % 5 + 1)),
                "name": f"POC Agent {index:02d}",
                "status": "ACTIVE",
            }
        )
    for index in range(1, 13):
        rows["sfa_products"].append(
            {
                "id": deterministic_id("sfa_product", str(index)),
                "product_code": f"POC-PROD-{index:02d}",
                "name": f"POC Product {index:02d}",
                "category": ("SIM", "DATA", "VOICE", "DEVICE")[index % 4],
            }
        )


def _sfa_facts(
    rows: dict[str, list[dict[str, Any]]],
    monthly_sales: Counter[str],
    rng: random.Random,
) -> None:
    for retailer in range(1, 26):
        retailer_id = deterministic_id("retailer", str(retailer))
        agent_id = deterministic_id("sales_agent", str((retailer - 1) % 10 + 1))
        for month in range(12):
            for product in range(1, 5):
                product_id = deterministic_id("sfa_product", str(product))
                occurred_at = START_AT + timedelta(days=month * 30 + retailer % 20)
                quantity = 5 + ((retailer + product + month) % 15)
                if retailer == 1 and month >= 9:
                    quantity += 25
                sale_id = deterministic_id("sale", f"{retailer}:{product}:{month}")
                event_id = _add_event(
                    rows, "SFA_SALE_RECORDED", "sale", sale_id, None, occurred_at
                )
                amount = Decimal(quantity * (100 + product * 50))
                rows["sales"].append(
                    {
                        "id": sale_id,
                        "retailer_id": retailer_id,
                        "product_id": product_id,
                        "quantity": quantity,
                        "amount": amount,
                        "occurred_at": occurred_at,
                        "sales_agent_id": agent_id,
                        "source_event_id": event_id,
                    }
                )
                inventory_id = deterministic_id("inventory", f"{retailer}:{product}:{month}")
                inventory_event = _add_event(
                    rows,
                    "INVENTORY_UPDATED",
                    "inventory",
                    inventory_id,
                    None,
                    occurred_at - timedelta(days=2),
                )
                rows["inventory_events"].append(
                    {
                        "id": inventory_id,
                        "retailer_id": retailer_id,
                        "product_id": product_id,
                        "event_type": "STOCK_IN",
                        "quantity": quantity + rng.randint(3, 12),
                        "occurred_at": occurred_at - timedelta(days=2),
                        "source_event_id": inventory_event,
                    }
                )
                monthly_sales[_month(occurred_at)] += float(amount)


def _add_event(
    rows: dict[str, list[dict[str, Any]]],
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    customer_id: UUID | None,
    occurred_at: datetime,
) -> UUID:
    key = f"{event_type}:{aggregate_id}"
    event_id = deterministic_id("event", key)
    outbox_id = deterministic_id("outbox", key)
    payload = {"dataset_version": DATASET_VERSION, "aggregate_type": aggregate_type}
    rows["activity_events"].append(
        {
            "id": event_id,
            "entity_type": aggregate_type,
            "entity_id": aggregate_id,
            "customer_id": customer_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "recorded_at": occurred_at,
            "source": DATASET_VERSION,
            "correlation_id": f"{DATASET_VERSION}:{aggregate_type}",
            "idempotency_key": f"{DATASET_VERSION}:{key}",
            "payload": payload,
        }
    )
    rows["outbox_events"].append(
        {
            "id": outbox_id,
            "event_id": event_id,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "created_at": occurred_at,
            "processed_at": None,
            "attempt_count": 0,
            "last_error": None,
            "status": "PENDING",
        }
    )
    return event_id


def _month(value: datetime) -> str:
    return value.strftime("%Y-%m")
