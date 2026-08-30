"""create locked postgresql schemas and tables

Revision ID: 0001_locked_schema
Revises:
Create Date: 2026-08-27
"""

from collections.abc import Sequence

from alembic import op

from telco_digital.infrastructure.postgres.models import SCHEMAS, Base

revision: str = "0001_locked_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
