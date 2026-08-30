from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from telco_digital.infrastructure.postgres.repositories import (
    SqlAccountRepository,
    SqlCustomerDeviceRepository,
    SqlCustomerRepository,
    SqlDeviceRepository,
    SqlEventRepository,
    SqlLedgerRepository,
    SqlOutboxRepository,
    SqlPlanRepository,
    SqlRechargeRepository,
    SqlServiceInteractionRepository,
    SqlSubscriptionRepository,
    SqlTravelRepository,
    SqlUsageRepository,
    SqlWarningRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        session = self.session
        self.customers = SqlCustomerRepository(session)
        self.accounts = SqlAccountRepository(session)
        self.devices = SqlDeviceRepository(session)
        self.customer_devices = SqlCustomerDeviceRepository(session)
        self.plans = SqlPlanRepository(session)
        self.subscriptions = SqlSubscriptionRepository(session)
        self.ledgers = SqlLedgerRepository(session)
        self.recharges = SqlRechargeRepository(session)
        self.usage_events = SqlUsageRepository(session)
        self.travels = SqlTravelRepository(session)
        self.service_interactions = SqlServiceInteractionRepository(session)
        self.events = SqlEventRepository(session)
        self.outbox = SqlOutboxRepository(session)
        self.warnings = SqlWarningRepository(session)
        return self

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        if self.session is not None:
            await self.session.close()
            self.session = None
