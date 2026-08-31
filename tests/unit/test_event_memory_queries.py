from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.application.commands.commands import CreateCustomerCommand, RecordTravelCommand
from telco_digital.application.seed import seed_demo_customers
from telco_digital.application.services.customer import create_customer
from telco_digital.application.services.travel import record_travel
from telco_digital.domain.entities import Travel
from telco_digital.domain.enums import AccountType
from telco_digital.intelligence.event_memory.uow import UnitOfWorkEventMemoryQueries

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


async def _peer_with_travel(uow, clock, *, ref: str, country: str, started_at: str) -> None:
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref=ref,
            home_country="Sri Lanka",
            account_type=AccountType.PREPAID,
            customer_since=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            device_ref=f"D-{ref}",
            correlation_id=f"test-{ref}",
        ),
        clock=clock,
    )
    await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref=ref,
            country=country,
            started_at=datetime.fromisoformat(started_at),
            correlation_id=f"test-{ref}",
        ),
        clock=clock,
    )


@pytest.mark.asyncio
async def test_uow_load_peers_uses_travel_candidates_not_all_customers(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    await _peer_with_travel(
        uow, clock, ref="PEER-SG", country="Singapore", started_at="2026-04-01T08:00:00+00:00"
    )
    await _peer_with_travel(
        uow, clock, ref="PEER-IN", country="India", started_at="2026-05-01T08:00:00+00:00"
    )

    async def fail_list_all():
        raise AssertionError("load_peers must not scan all customers")

    uow.customers.list_all = fail_list_all
    subject = await uow.customers.get_by_ref("U001")
    peers = await UnitOfWorkEventMemoryQueries(uow).load_peers(
        exclude_customer_id=subject.id,
        destination="SG",
        as_of=AS_OF,
        limit=10,
    )

    assert [bundle.customer_ref for bundle in peers] == ["PEER-SG"]
    assert all(bundle.customer_id != subject.id for bundle in peers)


@pytest.mark.asyncio
async def test_uow_load_peers_respects_limit_and_optional_destination(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    await _peer_with_travel(
        uow, clock, ref="PEER-A", country="Singapore", started_at="2026-04-01T08:00:00+00:00"
    )
    await _peer_with_travel(
        uow, clock, ref="PEER-B", country="India", started_at="2026-06-01T08:00:00+00:00"
    )

    subject = await uow.customers.get_by_ref("U001")
    queries = UnitOfWorkEventMemoryQueries(uow)
    unfiltered = await queries.load_peers(
        exclude_customer_id=subject.id,
        destination=None,
        as_of=AS_OF,
        limit=1,
    )
    assert [bundle.customer_ref for bundle in unfiltered] == ["PEER-B"]

    empty = await queries.load_peers(
        exclude_customer_id=subject.id,
        destination="JP",
        as_of=AS_OF,
        limit=10,
    )
    assert empty == ()


@pytest.mark.asyncio
async def test_list_peer_customer_ids_ignores_future_travel(uow) -> None:
    earlier = datetime.fromisoformat("2026-03-01T00:00:00+00:00")
    later = datetime.fromisoformat("2026-08-01T00:00:00+00:00")
    excluded = uuid4()
    peer = uuid4()
    await uow.travels.add(Travel(customer_id=peer, country_code="SG", started_at=later))
    await uow.travels.add(Travel(customer_id=excluded, country_code="SG", started_at=earlier))
    ids = await uow.travels.list_peer_customer_ids(
        exclude_customer_id=excluded,
        as_of=earlier,
        destination="SG",
        limit=25,
    )
    assert ids == []
