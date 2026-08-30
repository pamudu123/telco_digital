from datetime import datetime

import pytest
from dotenv import load_dotenv

from telco_digital.application.clock import FixedClock
from telco_digital.infrastructure.memory import InMemoryUnitOfWork

load_dotenv()


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(utc("2026-08-27T00:00:00+00:00"))
