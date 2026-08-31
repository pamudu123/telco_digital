from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from telco_digital.intelligence.event_memory import (
    EPISODE_SET_VERSION,
    CustomerTravelFacts,
    EventMemoryService,
    MatchRank,
    RawSubscription,
    RawTravel,
    RawUsage,
    extract_travel_episodes,
    match_episodes,
    situation_from_facts,
)

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")
MARCH_START = datetime.fromisoformat("2026-03-10T08:00:00+00:00")
MARCH_END = datetime.fromisoformat("2026-03-16T18:00:00+00:00")


def _facts(*, include_future_end: bool = False) -> CustomerTravelFacts:
    customer_id = uuid4()
    travel_id = uuid4()
    ended_at = (
        datetime.fromisoformat("2026-08-25T18:00:00+00:00") if include_future_end else MARCH_END
    )
    usage = [
        RawUsage(
            customer_id=customer_id,
            occurred_at=datetime.fromisoformat(when),
            data_mb=amount,
            country_code="SG",
        )
        for when, amount in (
            ("2026-03-10T20:00:00+00:00", Decimal("1800")),
            ("2026-03-11T20:00:00+00:00", Decimal("2100")),
            ("2026-03-12T20:00:00+00:00", Decimal("1900")),
            ("2026-03-13T20:00:00+00:00", Decimal("1700")),
            ("2026-03-14T20:00:00+00:00", Decimal("1600")),
            ("2026-03-15T20:00:00+00:00", Decimal("1400")),
            ("2026-03-16T12:00:00+00:00", Decimal("900")),
        )
    ]
    return CustomerTravelFacts(
        customer_id=customer_id,
        customer_ref="U001",
        travels=(
            RawTravel(
                id=travel_id,
                customer_id=customer_id,
                customer_ref="U001",
                destination="SG",
                started_at=MARCH_START,
                ended_at=ended_at,
            ),
        ),
        usage=tuple(usage),
        subscriptions=(
            RawSubscription(
                customer_id=customer_id,
                plan_code="ROAM_15",
                plan_type="ROAMING",
                plan_data_mb=15360,
                plan_country="SG",
                started_at=datetime.fromisoformat("2026-03-10T09:00:00+00:00"),
            ),
        ),
    )


def test_march_episode_has_duration_usage_plan_and_outcome() -> None:
    episodes = extract_travel_episodes(_facts(), AS_OF)
    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.destination_name == "Singapore"
    assert episode.duration_days == 6
    assert episode.metrics["usage_gb"] == 11.4
    assert episode.actions["plan_selected"] == "ROAM_15"
    assert episode.outcome == "No additional package required"


def test_future_trip_end_is_unknown_at_as_of() -> None:
    during = datetime.fromisoformat("2026-03-16T12:00:00+00:00")
    episodes = extract_travel_episodes(_facts(), during)
    assert episodes[0].duration_known is False
    assert episodes[0].end_at is None
    assert episodes[0].outcome == "Trip duration unknown at as_of"


def test_future_end_after_as_of_does_not_leak() -> None:
    episodes = extract_travel_episodes(_facts(include_future_end=True), AS_OF)
    assert episodes[0].duration_known is False
    assert episodes[0].end_at is None


def test_same_customer_same_destination_outranks_peers() -> None:
    own = extract_travel_episodes(_facts(), AS_OF)
    peer_id = uuid4()
    peers = extract_travel_episodes(
        CustomerTravelFacts(
            customer_id=peer_id,
            customer_ref="BG001",
            travels=(
                RawTravel(
                    id=uuid4(),
                    customer_id=peer_id,
                    customer_ref="BG001",
                    destination="SG",
                    started_at=datetime.fromisoformat("2026-01-01T08:00:00+00:00"),
                    ended_at=datetime.fromisoformat("2026-01-07T08:00:00+00:00"),
                ),
            ),
        ),
        AS_OF,
    )
    situation = situation_from_facts(_facts(), AS_OF, destination="SG")
    matches = match_episodes(situation=situation, own=own, peers=peers)
    assert matches[0].rank == MatchRank.SAME_CUSTOMER_SAME_SITUATION
    assert matches[0].episode.customer_ref == "U001"
    assert any(item.rank == MatchRank.SIMILAR_CUSTOMERS for item in matches)


@pytest.mark.asyncio
async def test_service_recalls_personal_history_first() -> None:
    facts = _facts()

    class Queries:
        async def load_customer(self, customer_ref: str, as_of: datetime):
            return facts

        async def load_peers(self, **kwargs):
            return ()

    result = await EventMemoryService(Queries()).recall("U001", AS_OF, destination="Singapore")
    assert result.episode_set_version == EPISODE_SET_VERSION
    assert result.current_situation.destination == "SG"
    assert result.current_situation.duration_known is False
    assert result.matches[0].episode.metrics["usage_gb"] == 11.4
    assert "duration is unknown" in result.unknowns[0]


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        extract_travel_episodes(_facts(), datetime(2026, 8, 20))


def test_postgres_adapter_bulk_loads_peer_facts() -> None:
    source = Path("src/telco_digital/infrastructure/postgres/event_memory.py").read_text(
        encoding="utf-8"
    )
    load_peers = source.split("async def load_peers", 1)[1]
    assert "await self._bundle(" not in load_peers
    assert "in_(customer_ids)" in source
    assert "in_(peer_ids)" in source


def test_uow_adapter_selects_peer_ids_from_travel_history() -> None:
    source = Path("src/telco_digital/intelligence/event_memory/uow.py").read_text(encoding="utf-8")
    load_peers = source.split("async def load_peers", 1)[1]
    assert "customers.list_all()" not in load_peers
    assert "list_peer_customer_ids" in load_peers
