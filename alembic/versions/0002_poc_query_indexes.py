"""add POC temporal, projection, transaction, and SFA query indexes

Revision ID: 0002_poc_query_indexes
Revises: 0001_locked_schema
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_poc_query_indexes"
down_revision: str | Sequence[str] | None = "0001_locked_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEXES = (
    ("ix_usage_customer_occurred", "usage_event", ["customer_id", "occurred_at"], "telco"),
    ("ix_recharge_customer_occurred", "recharge", ["customer_id", "occurred_at"], "telco"),
    ("ix_travel_customer_started", "travel", ["customer_id", "started_at"], "telco"),
    (
        "ix_interaction_customer_occurred",
        "service_interaction",
        ["customer_id", "occurred_at"],
        "telco",
    ),
    (
        "ix_balance_account_occurred",
        "balance_ledger",
        ["account_id", "occurred_at"],
        "telco",
    ),
    ("ix_activity_customer_occurred", "event", ["customer_id", "occurred_at"], "activity"),
    (
        "ix_outbox_status_created",
        "outbox_event",
        ["status", "created_at"],
        "integration",
    ),
    (
        "ix_money_customer_occurred",
        "transaction",
        ["customer_id", "occurred_at"],
        "money",
    ),
    (
        "ix_money_merchant_occurred",
        "transaction",
        ["merchant_id", "occurred_at"],
        "money",
    ),
    ("ix_sale_retailer_occurred", "sale", ["retailer_id", "occurred_at"], "sfa"),
    (
        "ix_inventory_retailer_product_occurred",
        "inventory_event",
        ["retailer_id", "product_id", "occurred_at"],
        "sfa",
    ),
)


def upgrade() -> None:
    for name, table, columns, schema in INDEXES:
        op.create_index(name, table, columns, schema=schema)


def downgrade() -> None:
    for name, table, _columns, schema in reversed(INDEXES):
        op.drop_index(name, table_name=table, schema=schema)
