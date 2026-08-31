import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from telco_digital.config import get_settings
from telco_digital.domain.enums import OutboxStatus
from telco_digital.infrastructure.postgres.models import OutboxEventModel
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.infrastructure.workers.outbox_worker import process_batch

pytestmark = pytest.mark.integration

requires_postgres = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not exported — configure PostgreSQL before running integration tests",
)


def integration_settings():
    return get_settings().model_copy(update={"database_pool_mode": "transaction"})


@requires_postgres
@pytest.mark.asyncio
async def test_worker_checkpoints_only_after_projection_success() -> None:
    engine = create_engine(integration_settings())
    factory = create_session_factory(engine)
    outbox_id = uuid4()
    event_id = uuid4()
    try:
        async with factory() as session, session.begin():
            session.add(
                OutboxEventModel(
                    id=outbox_id,
                    event_id=event_id,
                    event_type="POC_TEST",
                    aggregate_type="test",
                    aggregate_id=uuid4(),
                    payload={"test": True},
                    created_at=datetime.now(tz=UTC),
                    processed_at=None,
                    attempt_count=0,
                    last_error=None,
                    status=OutboxStatus.PENDING.value,
                )
            )

        async def project() -> dict[str, int]:
            return {"Customer": 1}

        assert await process_batch(factory, project, batch_size=1) == 1
        async with factory() as session:
            row = await session.scalar(
                select(OutboxEventModel).where(OutboxEventModel.id == outbox_id)
            )
            assert row is not None
            assert row.status == OutboxStatus.PROCESSED.value
            assert row.attempt_count == 1
            assert row.processed_at is not None
    finally:
        async with factory() as session, session.begin():
            await session.execute(delete(OutboxEventModel).where(OutboxEventModel.id == outbox_id))
        await engine.dispose()


@requires_postgres
@pytest.mark.asyncio
async def test_worker_records_retry_without_false_success() -> None:
    engine = create_engine(integration_settings())
    factory = create_session_factory(engine)
    outbox_id = uuid4()
    try:
        async with factory() as session, session.begin():
            session.add(
                OutboxEventModel(
                    id=outbox_id,
                    event_id=uuid4(),
                    event_type="POC_RETRY_TEST",
                    aggregate_type="test",
                    aggregate_id=uuid4(),
                    payload={"test": True},
                    created_at=datetime.now(tz=UTC),
                    processed_at=None,
                    attempt_count=0,
                    last_error=None,
                    status=OutboxStatus.PENDING.value,
                )
            )

        async def fail_projection() -> dict[str, int]:
            raise RuntimeError("temporary graph failure")

        with pytest.raises(RuntimeError, match="temporary graph failure"):
            await process_batch(factory, fail_projection, batch_size=1)

        async with factory() as session:
            row = await session.scalar(
                select(OutboxEventModel).where(OutboxEventModel.id == outbox_id)
            )
            assert row is not None
            assert row.status == OutboxStatus.PENDING.value
            assert row.attempt_count == 1
            assert row.processed_at is None
            assert "temporary graph failure" in (row.last_error or "")
    finally:
        async with factory() as session, session.begin():
            await session.execute(delete(OutboxEventModel).where(OutboxEventModel.id == outbox_id))
        await engine.dispose()


@requires_postgres
@pytest.mark.asyncio
async def test_worker_reclaims_processing_rows_after_restart() -> None:
    engine = create_engine(integration_settings())
    factory = create_session_factory(engine)
    outbox_id = uuid4()
    try:
        async with factory() as session, session.begin():
            session.add(
                OutboxEventModel(
                    id=outbox_id,
                    event_id=uuid4(),
                    event_type="POC_RECOVERY_TEST",
                    aggregate_type="test",
                    aggregate_id=uuid4(),
                    payload={"test": True},
                    created_at=datetime.now(tz=UTC),
                    processed_at=None,
                    attempt_count=1,
                    last_error=None,
                    status=OutboxStatus.PROCESSING.value,
                )
            )

        async def project() -> dict[str, int]:
            return {"Customer": 1}

        assert await process_batch(factory, project, batch_size=1) == 1
        async with factory() as session:
            row = await session.get(OutboxEventModel, outbox_id)
            assert row is not None
            assert row.status == OutboxStatus.PROCESSED.value
            assert row.attempt_count == 2
    finally:
        async with factory() as session, session.begin():
            await session.execute(delete(OutboxEventModel).where(OutboxEventModel.id == outbox_id))
        await engine.dispose()
