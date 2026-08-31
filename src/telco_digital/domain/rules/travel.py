"""Deterministic travel geography for the POC.

These are not a routing engine. They exist so Singapore → USA in one hour is
flagged as IMPOSSIBLE_TRAVEL while the event remains stored.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from telco_digital.domain.entities import Travel
from telco_digital.domain.value_objects import normalize_country

# Minimum realistic transit hours between country pairs (symmetric).
_MIN_HOURS: dict[frozenset[str], float] = {
    frozenset({"SG", "US"}): 18.0,
    frozenset({"LK", "US"}): 20.0,
    frozenset({"GB", "US"}): 7.0,
    frozenset({"SG", "LK"}): 3.5,
    frozenset({"SG", "MY"}): 1.0,
    frozenset({"SG", "TH"}): 2.0,
    frozenset({"SG", "GB"}): 13.0,
    frozenset({"SG", "IN"}): 4.0,
    frozenset({"LK", "IN"}): 1.5,
    frozenset({"LK", "GB"}): 11.0,
    frozenset({"LK", "TH"}): 3.5,
    frozenset({"MY", "TH"}): 1.5,
}

DEFAULT_INTERNATIONAL_HOURS = 8.0


def min_transit_hours(origin: str, destination: str) -> float:
    a = normalize_country(origin)
    b = normalize_country(destination)
    if a == b:
        return 0.0
    return _MIN_HOURS.get(frozenset({a, b}), DEFAULT_INTERNATIONAL_HOURS)


@dataclass(frozen=True, slots=True)
class LocationAtTime:
    country_code: str
    source: str  # "travel" | "home"
    since: datetime | None
    travel: Travel | None = None


def location_at(
    *,
    home_country: str,
    travels: list[Travel],
    as_of: datetime,
) -> LocationAtTime:
    """Location using only travels with started_at <= as_of.

    An open trip (ended_at is NULL) is treated as current if it has started.
    A closed trip is current while started_at <= as_of < ended_at.
    If several overlap, the latest started_at wins.
    """
    active: list[Travel] = []
    for travel in travels:
        if travel.started_at > as_of:
            continue
        if travel.ended_at is None or travel.ended_at > as_of:
            active.append(travel)
    if active:
        current = max(active, key=lambda t: t.started_at)
        return LocationAtTime(
            country_code=current.country_code,
            source="travel",
            since=current.started_at,
            travel=current,
        )
    latest_return = max(
        (
            travel.ended_at
            for travel in travels
            if travel.ended_at is not None and travel.ended_at <= as_of
        ),
        default=None,
    )
    return LocationAtTime(
        country_code=normalize_country(home_country),
        source="home",
        since=latest_return,
        travel=None,
    )


def is_impossible_travel(
    *,
    from_country: str,
    from_time: datetime,
    to_country: str,
    to_time: datetime,
) -> bool:
    origin = normalize_country(from_country)
    dest = normalize_country(to_country)
    if origin == dest:
        return False
    if to_time <= from_time:
        return True
    elapsed = to_time - from_time
    required = timedelta(hours=min_transit_hours(origin, dest))
    return elapsed < required
