from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from telco_digital.intelligence.features import (
    FEATURE_SET_VERSION,
    CustomerFeatureService,
    GraphFeatures,
    GraphFeatureService,
    TemporalFeatureService,
    snapshot_id,
)

AS_OF = datetime.fromisoformat("2026-08-31T23:59:00+00:00")


class TemporalQueries:
    def __init__(self, events: list[datetime]) -> None:
        self.customer_id = uuid4()
        self.events = events

    async def calculate(self, customer_ref: str, as_of: datetime):
        bounded = [event for event in self.events if as_of - timedelta(days=30) <= event <= as_of]
        return self.customer_id, {
            "usage": {"window_days": 30, "values": {"event_count_30d": len(bounded)}}
        }


class GraphQueries:
    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFeatures:
        return GraphFeatures(available=True, values={"customer_graph_degree": 3})


@pytest.mark.asyncio
async def test_features_are_versioned_and_exclude_future_events() -> None:
    temporal = TemporalQueries([AS_OF - timedelta(days=1), AS_OF + timedelta(seconds=1)])
    service = CustomerFeatureService(
        TemporalFeatureService(temporal), GraphFeatureService(GraphQueries())
    )
    result = await service.calculate("U001", AS_OF)
    assert result.feature_set_version == FEATURE_SET_VERSION
    assert result.temporal["usage"].values["event_count_30d"] == 1
    assert result.graph.values["customer_graph_degree"] == 3


def test_snapshot_identity_is_stable_and_as_of_sensitive() -> None:
    customer_id = uuid4()
    assert snapshot_id(customer_id, AS_OF) == snapshot_id(customer_id, AS_OF)
    assert snapshot_id(customer_id, AS_OF) != snapshot_id(customer_id, AS_OF - timedelta(days=1))
    with pytest.raises(ValueError, match="timezone-aware"):
        snapshot_id(customer_id, datetime(2026, 8, 31))


@pytest.mark.asyncio
async def test_graph_failure_is_unknown_not_zero() -> None:
    class BrokenGraph:
        async def calculate(self, customer_ref: str, as_of: datetime):
            raise ConnectionError("offline")

    service = CustomerFeatureService(
        TemporalFeatureService(TemporalQueries([])), GraphFeatureService(BrokenGraph())
    )
    result = await service.calculate("U001", AS_OF)
    assert result.graph.available is False
    assert result.graph.values == {}
    assert "not assumed to be zero" in result.graph.unknowns[0]
