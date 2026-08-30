"""Single-worker POC outbox checkpointing for the Neo4j projection."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from telco_digital.domain.enums import OutboxStatus
from telco_digital.infrastructure.postgres.models import OutboxEventModel

Projection = Callable[[], Awaitable[dict[str, int]]]


async def process_batch(
    session_factory: async_sessionmaker[AsyncSession],
    project: Projection,
    *,
    batch_size: int = 500,
    max_attempts: int = 3,
    clock: Callable[[], datetime] | None = None,
) -> int:
    """Claim one batch, rebuild the graph, and checkpoint only after success."""
    now = clock or (lambda: datetime.now(tz=UTC))
    async with session_factory() as session, session.begin():
        rows = list(
            (
                await session.execute(
                    select(OutboxEventModel)
                    .where(OutboxEventModel.status == OutboxStatus.PENDING.value)
                    .order_by(OutboxEventModel.created_at, OutboxEventModel.id)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).scalars()
        )
        ids = [row.id for row in rows]
        if not ids:
            return 0
        await session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id.in_(ids))
            .values(
                status=OutboxStatus.PROCESSING.value,
                attempt_count=OutboxEventModel.attempt_count + 1,
                last_error=None,
            )
        )

    try:
        await project()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:2000]
        async with session_factory() as session, session.begin():
            retry_rows = (
                await session.execute(
                    select(OutboxEventModel.id, OutboxEventModel.attempt_count).where(
                        OutboxEventModel.id.in_(ids)
                    )
                )
            ).all()
            for event_id, attempt_count in retry_rows:
                status = (
                    OutboxStatus.FAILED.value
                    if attempt_count >= max_attempts
                    else OutboxStatus.PENDING.value
                )
                await session.execute(
                    update(OutboxEventModel)
                    .where(OutboxEventModel.id == event_id)
                    .values(status=status, last_error=error)
                )
        raise

    async with session_factory() as session, session.begin():
        await session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id.in_(ids))
            .values(
                status=OutboxStatus.PROCESSED.value,
                processed_at=now(),
                last_error=None,
            )
        )
    return len(ids)


async def drain(
    session_factory: async_sessionmaker[AsyncSession],
    project: Projection,
    *,
    batch_size: int = 500,
) -> int:
    total = 0
    while processed := await process_batch(session_factory, project, batch_size=batch_size):
        total += processed
    return total


def event_ids(rows: list[OutboxEventModel]) -> list[UUID]:
    """Small diagnostic helper retained for worker tests and logs."""
    return [row.id for row in rows]


async def run_once(*, batch_size: int = 25_000) -> int:
    """Build production dependencies and process a single POC batch."""
    from neo4j import GraphDatabase

    from telco_digital.config import get_settings
    from telco_digital.infrastructure.neo4j.projector import GraphProjector
    from telco_digital.infrastructure.neo4j.repository import GraphRepository
    from telco_digital.infrastructure.postgres.graph_snapshot import load_graph_snapshot
    from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async def project() -> dict[str, int]:
        snapshot = await load_graph_snapshot(engine)

        def write() -> dict[str, int]:
            with GraphDatabase.driver(
                settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
            ) as driver:
                driver.verify_connectivity()
                return GraphProjector(GraphRepository(driver)).rebuild(snapshot)

        return await asyncio.to_thread(write)

    try:
        return await process_batch(session_factory, project, batch_size=batch_size)
    finally:
        await engine.dispose()
