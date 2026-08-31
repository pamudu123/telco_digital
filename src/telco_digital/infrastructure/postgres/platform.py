"""PostgreSQL queries for outbox projection lag. SQL stays here."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.application.queries.platform import OutboxLagSnapshot
from telco_digital.domain.enums import OutboxStatus
from telco_digital.infrastructure.postgres.models import OutboxEventModel


class PostgresProjectionLagQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot(self) -> OutboxLagSnapshot:
        stmt = select(
            OutboxEventModel.status,
            func.count(),
            func.min(OutboxEventModel.created_at),
            func.max(OutboxEventModel.processed_at),
        ).group_by(OutboxEventModel.status)
        rows = (await self.session.execute(stmt)).all()
        pending = processing = failed = processed = 0
        oldest_pending_at: datetime | None = None
        newest_processed_at: datetime | None = None
        for status, count, oldest_created, newest_processed in rows:
            value = int(count or 0)
            if status == OutboxStatus.PENDING.value:
                pending = value
                oldest_pending_at = oldest_created
            elif status == OutboxStatus.PROCESSING.value:
                processing = value
            elif status == OutboxStatus.FAILED.value:
                failed = value
            elif status == OutboxStatus.PROCESSED.value:
                processed = value
                newest_processed_at = newest_processed
        return OutboxLagSnapshot(
            pending=pending,
            processing=processing,
            failed=failed,
            processed=processed,
            oldest_pending_at=oldest_pending_at,
            newest_processed_at=newest_processed_at,
        )
