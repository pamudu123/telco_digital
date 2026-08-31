"""Scenario: FastAPI command adapters write through UnitOfWork."""

import asyncio

from fastapi.testclient import TestClient
from tests.helpers import utc

from telco_digital.api.app import create_app
from telco_digital.api.deps import get_uow
from telco_digital.application.clock import FixedClock
from telco_digital.application.seed import seed_demo_customers
from telco_digital.config import Settings
from telco_digital.infrastructure.memory import InMemoryUnitOfWork


def test_recharge_command_is_visible_on_customer_state() -> None:
    uow = InMemoryUnitOfWork()
    asyncio.run(seed_demo_customers(uow, clock=FixedClock(utc("2026-08-20T12:00:00+00:00"))))
    app = create_app(Settings(showcase_enabled=True, api_environment="test"))
    app.dependency_overrides[get_uow] = lambda: uow
    with TestClient(app) as client:
        before = client.get(
            "/api/v1/customers/U001/state",
            params={"as_of": "2026-08-21T00:00:00+00:00"},
        )
        assert before.status_code == 200
        posted = client.post(
            "/api/v1/commands/recharge",
            json={
                "customer_ref": "U001",
                "amount": "500.00",
                "occurred_at": "2026-08-21T00:00:00+00:00",
                "correlation_id": "scenario-api-recharge",
            },
        )
        assert posted.status_code == 200
        payload = posted.json()
        assert payload["correlation_id"] == "scenario-api-recharge"
        assert payload["command"] == "record_recharge"
        after = client.get(
            "/api/v1/customers/U001/state",
            params={"as_of": "2026-08-21T00:00:00+00:00"},
        )
    assert after.status_code == 200
    assert float(after.json()["balance_amount"]) == float(before.json()["balance_amount"]) + 500
    pending = asyncio.run(uow.outbox.list_pending())
    assert any(str(item.event_id) == payload["event_id"] for item in pending)
