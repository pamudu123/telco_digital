"""Versioned, point-in-time customer feature contracts and orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict

FEATURE_SET_VERSION = "customer-features-v1"
FEATURE_NAMESPACE = UUID("7ec9b04a-058c-4bd5-8fcb-35d960d742b8")


class FeatureGroup(BaseModel):
    model_config = ConfigDict(frozen=True)
    window_days: int | None = None
    values: dict[str, Any]


class GraphFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)
    available: bool
    values: dict[str, int | float | None]
    unknowns: tuple[str, ...] = ()


class CustomerFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    feature_set_version: str = FEATURE_SET_VERSION
    temporal: dict[str, FeatureGroup]
    graph: GraphFeatures
    provenance: tuple[str, ...]
    unknowns: tuple[str, ...] = ()


class TemporalFeatureQueries(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> tuple[UUID, dict]: ...


class GraphFeatureQueries(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFeatures: ...


def validate_as_of(as_of: datetime) -> None:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")


def snapshot_id(customer_id: UUID, as_of: datetime, version: str = FEATURE_SET_VERSION) -> UUID:
    validate_as_of(as_of)
    normalized = as_of.astimezone(UTC).isoformat()
    return uuid5(FEATURE_NAMESPACE, f"customer:{customer_id}:{normalized}:{version}")


class TemporalFeatureService:
    def __init__(self, queries: TemporalFeatureQueries) -> None:
        self.queries = queries

    async def calculate(self, customer_ref: str, as_of: datetime) -> tuple[UUID, dict]:
        validate_as_of(as_of)
        return await self.queries.calculate(customer_ref, as_of)


class GraphFeatureService:
    def __init__(self, queries: GraphFeatureQueries) -> None:
        self.queries = queries

    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFeatures:
        validate_as_of(as_of)
        return await self.queries.calculate(customer_ref, as_of)


class CustomerFeatureService:
    def __init__(self, temporal: TemporalFeatureService, graph: GraphFeatureService) -> None:
        self.temporal = temporal
        self.graph = graph

    async def calculate(self, customer_ref: str, as_of: datetime) -> CustomerFeatures:
        customer_id, result = await self.temporal.calculate(customer_ref, as_of)
        try:
            graph = await self.graph.calculate(customer_ref, as_of)
        except Exception:
            graph = GraphFeatures(
                available=False,
                values={},
                unknowns=(
                    "Neo4j graph features are unavailable; values are not assumed to be zero.",
                ),
            )
        unknowns = tuple(graph.unknowns)
        return CustomerFeatures(
            customer_id=customer_id,
            customer_ref=customer_ref,
            as_of=as_of,
            computed_at=datetime.now(tz=UTC),
            temporal={key: FeatureGroup(**value) for key, value in result.items()},
            graph=graph,
            provenance=("PostgreSQL point-in-time facts", "Neo4j rebuildable projection"),
            unknowns=unknowns,
        )
