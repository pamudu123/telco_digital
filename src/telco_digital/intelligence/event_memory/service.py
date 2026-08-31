"""Travel episode extraction and similar-event matching (Milestone 5).

Episodes are derived from recorded facts at an explicit ``as_of``. They are
not persisted and are never a source of truth.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.domain.value_objects import display_country, normalize_country
from telco_digital.intelligence.features.service import validate_as_of

EPISODE_SET_VERSION = "travel-episodes-v1"
MB_PER_GB = Decimal("1000")


class MatchRank(StrEnum):
    SAME_CUSTOMER_SAME_SITUATION = "SAME_CUSTOMER_SAME_SITUATION"
    SAME_CUSTOMER_SIMILAR_SITUATION = "SAME_CUSTOMER_SIMILAR_SITUATION"
    SIMILAR_CUSTOMERS = "SIMILAR_CUSTOMERS"
    POPULATION = "POPULATION"


class RawTravel(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    customer_id: UUID
    customer_ref: str
    destination: str
    started_at: datetime
    ended_at: datetime | None = None


class RawUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    occurred_at: datetime
    data_mb: Decimal
    country_code: str


class RawSubscription(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    plan_code: str
    plan_type: str
    plan_data_mb: int
    plan_country: str | None = None
    started_at: datetime
    ended_at: datetime | None = None


class CustomerTravelFacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    customer_ref: str
    travels: tuple[RawTravel, ...] = ()
    usage: tuple[RawUsage, ...] = ()
    subscriptions: tuple[RawSubscription, ...] = ()


class EventMemoryQueries(Protocol):
    async def load_customer(self, customer_ref: str, as_of: datetime) -> CustomerTravelFacts: ...

    async def load_peers(
        self,
        *,
        exclude_customer_id: UUID,
        destination: str | None,
        as_of: datetime,
        limit: int = 25,
    ) -> tuple[CustomerTravelFacts, ...]: ...


class TravelSituation(BaseModel):
    model_config = ConfigDict(frozen=True)

    destination: str | None = None
    destination_name: str | None = None
    destination_known: bool = False
    duration_known: bool = False
    duration_days: int | None = None
    started_at: datetime | None = None
    current_travel_id: UUID | None = None
    source: str = "unknown"


class TravelEpisode(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_type: str = "TRAVEL"
    customer_id: UUID
    customer_ref: str
    travel_id: UUID
    destination: str
    destination_name: str
    start_at: datetime
    end_at: datetime | None = None
    duration_days: int | None = None
    duration_known: bool
    context: dict[str, str | None]
    actions: dict[str, str | None]
    outcome: str
    metrics: dict[str, float | int | None]
    provenance: tuple[str, ...] = ("Derived from PostgreSQL travel, usage and subscription facts",)


class EpisodeMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode: TravelEpisode
    rank: MatchRank
    similarity: float
    reasons: tuple[str, ...]


class CustomerContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    episode_set_version: str = EPISODE_SET_VERSION
    current_situation: TravelSituation
    historical_episodes: tuple[TravelEpisode, ...]
    matches: tuple[EpisodeMatch, ...]
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "PostgreSQL point-in-time facts",
        "Episodes are derived and not persisted",
    )


def _effective_end(travel: RawTravel, as_of: datetime) -> datetime | None:
    if travel.ended_at is None or travel.ended_at > as_of:
        return None
    return travel.ended_at


def _duration_days(start: datetime, end: datetime | None) -> int | None:
    if end is None:
        return None
    return max(0, (end - start).days)


def _usage_mb(
    usage: tuple[RawUsage, ...],
    *,
    customer_id: UUID,
    destination: str,
    start: datetime,
    end: datetime,
) -> Decimal:
    total = Decimal("0")
    for row in usage:
        if row.customer_id != customer_id:
            continue
        if row.country_code != destination:
            continue
        if row.occurred_at < start or row.occurred_at > end:
            continue
        total += row.data_mb
    return total


def _plan_during_trip(
    subscriptions: tuple[RawSubscription, ...],
    *,
    customer_id: UUID,
    destination: str,
    start: datetime,
    bound: datetime,
) -> RawSubscription | None:
    chosen: list[RawSubscription] = []
    for row in subscriptions:
        if row.customer_id != customer_id:
            continue
        if row.started_at < start or row.started_at > bound:
            continue
        if row.plan_type != "ROAMING":
            continue
        chosen.append(row)
    if not chosen:
        return None
    matching = [row for row in chosen if row.plan_country == destination]
    pool = matching or chosen
    return max(pool, key=lambda row: row.started_at)


def _outcome(
    *,
    duration_known: bool,
    plan_code: str | None,
    plan_data_mb: int | None,
    usage_mb: Decimal,
) -> str:
    if not duration_known:
        return "Trip duration unknown at as_of"
    if plan_code is None:
        return "No roaming plan selected during the trip"
    if plan_data_mb is not None and usage_mb <= Decimal(plan_data_mb):
        return "No additional package required"
    if plan_data_mb is not None and usage_mb > Decimal(plan_data_mb):
        return "Usage exceeded the selected roaming plan"
    return f"Selected {plan_code}"


def extract_travel_episodes(
    facts: CustomerTravelFacts,
    as_of: datetime,
    *,
    exclude_travel_id: UUID | None = None,
) -> tuple[TravelEpisode, ...]:
    validate_as_of(as_of)
    episodes: list[TravelEpisode] = []
    for travel in facts.travels:
        if travel.started_at > as_of:
            continue
        if exclude_travel_id is not None and travel.id == exclude_travel_id:
            continue
        end_at = _effective_end(travel, as_of)
        bound = end_at or as_of
        usage_mb = _usage_mb(
            facts.usage,
            customer_id=facts.customer_id,
            destination=travel.destination,
            start=travel.started_at,
            end=bound,
        )
        plan = _plan_during_trip(
            facts.subscriptions,
            customer_id=facts.customer_id,
            destination=travel.destination,
            start=travel.started_at,
            bound=bound,
        )
        duration_known = end_at is not None
        duration_days = _duration_days(travel.started_at, end_at)
        plan_code = plan.plan_code if plan else None
        plan_data_mb = plan.plan_data_mb if plan else None
        usage_gb = float((usage_mb / MB_PER_GB).quantize(Decimal("0.1")))
        episodes.append(
            TravelEpisode(
                customer_id=facts.customer_id,
                customer_ref=facts.customer_ref,
                travel_id=travel.id,
                destination=travel.destination,
                destination_name=display_country(travel.destination),
                start_at=travel.started_at,
                end_at=end_at,
                duration_days=duration_days,
                duration_known=duration_known,
                context={
                    "destination": travel.destination,
                    "destination_name": display_country(travel.destination),
                },
                actions={"plan_selected": plan_code},
                outcome=_outcome(
                    duration_known=duration_known,
                    plan_code=plan_code,
                    plan_data_mb=plan_data_mb,
                    usage_mb=usage_mb,
                ),
                metrics={
                    "usage_mb": float(usage_mb),
                    "usage_gb": usage_gb,
                    "duration_days": duration_days,
                    "plan_data_mb": plan_data_mb,
                },
            )
        )
    episodes.sort(key=lambda item: item.start_at, reverse=True)
    return tuple(episodes)


def situation_from_facts(
    facts: CustomerTravelFacts,
    as_of: datetime,
    *,
    destination: str | None = None,
) -> TravelSituation:
    validate_as_of(as_of)
    active = [
        travel
        for travel in facts.travels
        if travel.started_at <= as_of and (travel.ended_at is None or travel.ended_at > as_of)
    ]
    current = max(active, key=lambda travel: travel.started_at) if active else None
    if destination:
        dest = normalize_country(destination)
        if current is not None and current.destination == dest:
            end_at = _effective_end(current, as_of)
            return TravelSituation(
                destination=dest,
                destination_name=display_country(dest),
                destination_known=True,
                duration_known=end_at is not None,
                duration_days=_duration_days(current.started_at, end_at),
                started_at=current.started_at,
                current_travel_id=current.id,
                source="travel",
            )
        return TravelSituation(
            destination=dest,
            destination_name=display_country(dest),
            destination_known=True,
            duration_known=False,
            source="query",
        )
    if current is not None:
        end_at = _effective_end(current, as_of)
        return TravelSituation(
            destination=current.destination,
            destination_name=display_country(current.destination),
            destination_known=True,
            duration_known=end_at is not None,
            duration_days=_duration_days(current.started_at, end_at),
            started_at=current.started_at,
            current_travel_id=current.id,
            source="travel",
        )
    return TravelSituation(source="none")


def _rank(same_customer: bool, same_destination: bool) -> MatchRank:
    if same_customer and same_destination:
        return MatchRank.SAME_CUSTOMER_SAME_SITUATION
    if same_customer:
        return MatchRank.SAME_CUSTOMER_SIMILAR_SITUATION
    if same_destination:
        return MatchRank.SIMILAR_CUSTOMERS
    return MatchRank.POPULATION


def score_episode(
    episode: TravelEpisode, situation: TravelSituation, *, same_customer: bool
) -> EpisodeMatch:
    same_destination = bool(
        situation.destination_known
        and situation.destination is not None
        and episode.destination == situation.destination
    )
    score = 0.0
    reasons: list[str] = []
    if same_customer:
        score += 0.30
        reasons.append("Same customer")
    if same_destination:
        score += 0.55
        reasons.append("Same destination")
    if situation.duration_known and episode.duration_known:
        delta = abs((episode.duration_days or 0) - (situation.duration_days or 0))
        if delta <= 2:
            score += 0.10
            reasons.append("Similar duration")
        else:
            score += 0.03
    elif (not situation.duration_known) and episode.duration_known:
        score += 0.05
        reasons.append("Historical duration available as a prior")
    if episode.actions.get("plan_selected"):
        score += 0.05
        reasons.append("Roaming plan selected on the historical trip")
    rank = _rank(same_customer, same_destination)
    return EpisodeMatch(
        episode=episode,
        rank=rank,
        similarity=round(min(score, 1.0), 4),
        reasons=tuple(reasons),
    )


def match_episodes(
    *,
    situation: TravelSituation,
    own: tuple[TravelEpisode, ...],
    peers: tuple[TravelEpisode, ...] = (),
    limit: int = 8,
) -> tuple[EpisodeMatch, ...]:
    matches = [score_episode(episode, situation, same_customer=True) for episode in own]
    matches.extend(score_episode(episode, situation, same_customer=False) for episode in peers)
    rank_order = {rank: index for index, rank in enumerate(MatchRank)}
    matches.sort(
        key=lambda item: (
            rank_order[item.rank],
            -item.similarity,
            -item.episode.start_at.timestamp(),
        )
    )
    return tuple(matches[:limit])


def _unknowns(
    situation: TravelSituation,
    own: tuple[TravelEpisode, ...],
    matches: tuple[EpisodeMatch, ...],
) -> tuple[str, ...]:
    unknowns: list[str] = []
    if not situation.destination_known:
        unknowns.append("Current destination is unknown; matching used historical travel only.")
    if situation.destination_known and not situation.duration_known:
        unknowns.append("Current trip duration is unknown.")
    if not own:
        unknowns.append("No historical travel episodes exist at this as_of.")
    elif situation.destination_known and not any(
        episode.destination == situation.destination for episode in own
    ):
        unknowns.append("No same-destination historical episode exists for this customer.")
    if situation.destination_known and not matches:
        unknowns.append("No similar episodes were retrieved.")
    return tuple(unknowns)


class EventMemoryService:
    def __init__(self, queries: EventMemoryQueries) -> None:
        self.queries = queries

    async def recall(
        self,
        customer_ref: str,
        as_of: datetime,
        *,
        destination: str | None = None,
    ) -> CustomerContext:
        validate_as_of(as_of)
        facts = await self.queries.load_customer(customer_ref, as_of)
        situation = situation_from_facts(facts, as_of, destination=destination)
        own = extract_travel_episodes(facts, as_of, exclude_travel_id=situation.current_travel_id)
        peer_facts = await self.queries.load_peers(
            exclude_customer_id=facts.customer_id,
            destination=situation.destination,
            as_of=as_of,
        )
        peers = tuple(
            episode for bundle in peer_facts for episode in extract_travel_episodes(bundle, as_of)
        )
        matches = match_episodes(situation=situation, own=own, peers=peers)
        return CustomerContext(
            customer_id=facts.customer_id,
            customer_ref=facts.customer_ref,
            as_of=as_of,
            computed_at=datetime.now(tz=UTC),
            current_situation=situation,
            historical_episodes=own,
            matches=matches,
            unknowns=_unknowns(situation, own, matches),
        )
