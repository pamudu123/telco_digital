import asyncio
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.helpers import utc

from telco_digital.api.app import create_app
from telco_digital.api.deps import get_uow
from telco_digital.application.clock import FixedClock
from telco_digital.application.commands.commands import GetCustomerStateQuery
from telco_digital.application.seed import seed_demo_customers
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.config import Settings
from telco_digital.infrastructure.memory import InMemoryUnitOfWork


def _seeded_uow() -> InMemoryUnitOfWork:
    uow = InMemoryUnitOfWork()
    asyncio.run(seed_demo_customers(uow, clock=FixedClock(utc("2026-08-20T12:00:00+00:00"))))
    return uow


def _client(uow: InMemoryUnitOfWork) -> TestClient:
    app = create_app(Settings(showcase_enabled=True, api_environment="test"))
    app.dependency_overrides[get_uow] = lambda: uow
    return TestClient(app)


def test_recharge_command_writes_event_and_returns_correlation_id() -> None:
    uow = _seeded_uow()
    with _client(uow) as client:
        response = client.post(
            "/api/v1/commands/recharge",
            json={
                "customer_ref": "U001",
                "amount": "250.00",
                "occurred_at": "2026-08-20T12:00:00+00:00",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["command"] == "record_recharge"
    assert body["source"] == "command_adapter"
    assert body["correlation_id"]
    assert body["event_id"]
    pending = asyncio.run(uow.outbox.list_pending())
    assert any(str(item.event_id) == body["event_id"] for item in pending)


def test_travel_command_records_country() -> None:
    uow = _seeded_uow()
    with _client(uow) as client:
        response = client.post(
            "/api/v1/commands/travel",
            json={
                "customer_ref": "U001",
                "country": "US",
                "started_at": "2026-08-20T12:00:00+00:00",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["command"] == "record_travel"
    assert body["extra"]["country_code"] == "US"
    assert body["correlation_id"]


def test_plan_purchase_unknown_plan_returns_404() -> None:
    uow = _seeded_uow()
    with _client(uow) as client:
        response = client.post(
            "/api/v1/commands/plan-purchase",
            json={
                "customer_ref": "U001",
                "plan_code": "INVENTED_PLAN",
                "occurred_at": "2026-08-20T12:00:00+00:00",
            },
        )
    assert response.status_code == 404


def test_recharge_naive_timestamp_returns_422() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        response = client.post(
            "/api/v1/commands/recharge",
            json={
                "customer_ref": "U001",
                "amount": "100",
                "occurred_at": "2026-08-20T12:00:00",
            },
        )
    assert response.status_code == 422


def test_unknown_customer_command_returns_404() -> None:
    uow = InMemoryUnitOfWork()
    with _client(uow) as client:
        response = client.post(
            "/api/v1/commands/recharge",
            json={
                "customer_ref": "NOPE",
                "amount": "100",
                "occurred_at": "2026-08-20T12:00:00+00:00",
            },
        )
    assert response.status_code == 404


def test_state_query_adapter_returns_observed_facts() -> None:
    uow = _seeded_uow()
    as_of = utc("2026-08-20T12:00:00+00:00")
    expected = asyncio.run(
        get_customer_state(uow, GetCustomerStateQuery(customer_ref="U001", as_of=as_of))
    )
    with _client(uow) as client:
        response = client.get(
            "/api/v1/customers/U001/state",
            params={"as_of": "2026-08-20T12:00:00+00:00"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["customer_ref"] == "U001"
    assert Decimal(body["balance_amount"]) == expected.balance_amount


def test_timeline_query_adapter_returns_entries() -> None:
    uow = _seeded_uow()
    with _client(uow) as client:
        response = client.get(
            "/api/v1/customers/U001/timeline",
            params={"as_of": "2026-08-20T12:00:00+00:00"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "live_database"
    assert body["entries"]
    assert all("event_type" in item for item in body["entries"])
