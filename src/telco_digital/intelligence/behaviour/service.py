"""Deterministic behaviour traits derived at an explicit ``as_of``.

Traits are computed from capability-02 features and capability-03 travel
episodes. They are not persisted and are never a source of truth.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from telco_digital.intelligence.event_memory import EventMemoryService, TravelEpisode
from telco_digital.intelligence.features import CustomerFeatures, CustomerFeatureService
from telco_digital.intelligence.features.service import validate_as_of

BEHAVIOUR_SET_VERSION = "customer-behaviour-v1"


class BehaviourTrait(BaseModel):
    model_config = ConfigDict(frozen=True)

    trait: str
    confidence: float
    evidence: dict[str, Any]
    source: str = "rule"


class CustomerBehaviour(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "derived_live"
    customer_id: UUID
    customer_ref: str
    as_of: datetime
    computed_at: datetime
    behaviour_set_version: str = BEHAVIOUR_SET_VERSION
    traits: tuple[BehaviourTrait, ...]
    unknowns: tuple[str, ...] = ()
    provenance: tuple[str, ...] = (
        "PostgreSQL point-in-time features",
        "Derived travel episodes",
        "Traits are derived and not persisted",
    )


class FeatureCalculator(Protocol):
    async def calculate(self, customer_ref: str, as_of: datetime) -> CustomerFeatures: ...


class EpisodeRecaller(Protocol):
    async def recall(
        self, customer_ref: str, as_of: datetime, *, destination: str | None = None
    ) -> Any: ...


def _values(features: CustomerFeatures, group: str) -> dict[str, Any]:
    item = features.temporal.get(group)
    return dict(item.values) if item is not None else {}


def _number(values: dict[str, Any], key: str) -> float:
    raw = values.get(key)
    if raw is None:
        return 0.0
    return float(raw)


def _band(steps: int, *, base: float = 0.7, step: float = 0.05, cap: float = 0.95) -> float:
    return round(min(cap, base + step * max(0, steps)), 2)


def _episode_usage_gb(episodes: tuple[TravelEpisode, ...]) -> float:
    if not episodes:
        return 0.0
    return max(float(episode.metrics.get("usage_gb") or 0) for episode in episodes)


def _episode_roaming_days(episodes: tuple[TravelEpisode, ...]) -> int:
    return sum(int(episode.duration_days or 0) for episode in episodes)


def assign_traits(
    features: CustomerFeatures,
    episodes: tuple[TravelEpisode, ...] = (),
) -> tuple[BehaviourTrait, ...]:
    recharge = _values(features, "recharge")
    usage = _values(features, "usage")
    travel = _values(features, "travel")
    service = _values(features, "service")
    campaign = _values(features, "campaign")

    small = int(_number(recharge, "small_recharge_count_30d"))
    frequent_small = bool(recharge.get("frequent_small_recharge_evidence"))
    amount_30d = _number(recharge, "amount_30d")
    mb_30d = _number(usage, "data_mb_30d")
    mb_90d = _number(usage, "data_mb_90d")
    change_ratio = usage.get("data_mb_change_ratio")
    trips = int(_number(travel, "trip_count_365d"))
    roam_days = int(_number(travel, "roaming_days_365d"))
    complaints = int(_number(service, "complaint_count_90d"))
    open_count = int(_number(service, "open_count"))
    conversions = int(_number(campaign, "conversion_count_90d"))
    conversion_rate = campaign.get("conversion_rate_90d")
    episode_gb = _episode_usage_gb(episodes)
    episode_days = _episode_roaming_days(episodes)

    traits: list[BehaviourTrait] = []

    if small >= 3 or frequent_small:
        traits.append(
            BehaviourTrait(
                trait="PRICE_SENSITIVE",
                confidence=_band(small - 3),
                evidence={
                    "small_recharge_frequency": "high" if small >= 4 else "medium",
                    "small_recharge_count_30d": small,
                    "frequent_small_recharge_evidence": frequent_small,
                },
            )
        )

    if (trips >= 1 and roam_days >= 5) or (episodes and episode_days >= 5):
        traits.append(
            BehaviourTrait(
                trait="FREQUENT_TRAVELLER",
                confidence=_band(max(trips, len(episodes)) - 1, base=0.75),
                evidence={
                    "trip_count_365d": trips,
                    "roaming_days_365d": roam_days,
                    "historical_travel_episodes": len(episodes),
                },
            )
        )

    if mb_30d >= 2000 or mb_90d >= 5000 or episode_gb >= 8:
        traits.append(
            BehaviourTrait(
                trait="HEAVY_DATA_USER",
                confidence=_band(int(max(mb_30d, episode_gb * 1000) / 2000) - 1, base=0.72),
                evidence={
                    "data_mb_30d": mb_30d,
                    "data_mb_90d": mb_90d,
                    "episode_usage_gb": episode_gb,
                },
            )
        )

    if amount_30d >= 2000 and small < 3:
        traits.append(
            BehaviourTrait(
                trait="HIGH_VALUE",
                confidence=_band(int(amount_30d / 2000) - 1, base=0.78),
                evidence={
                    "recharge_amount_30d": amount_30d,
                    "small_recharge_count_30d": small,
                },
            )
        )

    declining_from_ratio = change_ratio is not None and float(change_ratio) < 0 and complaints >= 1
    declining_from_complaints = complaints >= 1 and open_count >= 1 and mb_30d < 500
    if declining_from_ratio or declining_from_complaints:
        traits.append(
            BehaviourTrait(
                trait="DECLINING_ENGAGEMENT",
                confidence=0.8 if declining_from_ratio else 0.7,
                evidence={
                    "data_mb_change_ratio": change_ratio,
                    "complaint_count_90d": complaints,
                    "open_count": open_count,
                    "data_mb_30d": mb_30d,
                },
            )
        )

    if conversions >= 1 or (conversion_rate is not None and float(conversion_rate) >= 0.2):
        traits.append(
            BehaviourTrait(
                trait="PROMOTION_RESPONSIVE",
                confidence=_band(max(conversions - 1, 0), base=0.76),
                evidence={
                    "conversion_count_90d": conversions,
                    "conversion_rate_90d": conversion_rate,
                    "discount_campaign_response": "high",
                },
            )
        )

    if mb_30d >= 4000 or episode_gb >= 10:
        traits.append(
            BehaviourTrait(
                trait="STREAMING_HEAVY",
                confidence=0.55,
                evidence={
                    "data_mb_30d": mb_30d,
                    "episode_usage_gb": episode_gb,
                    "note": "Usage-type share is not in customer-features-v1; volume is a proxy.",
                },
            )
        )

    traits.sort(key=lambda item: (-item.confidence, item.trait))
    return tuple(traits)


def _unknowns(features: CustomerFeatures, traits: tuple[BehaviourTrait, ...]) -> tuple[str, ...]:
    unknowns = list(features.unknowns)
    if not traits:
        unknowns.append("No behaviour trait met the evidence threshold at this as_of.")
    usage = _values(features, "usage")
    if usage.get("data_mb_change_ratio") is None:
        unknowns.append(
            "Usage change ratio is unknown because the previous 30-day window is empty."
        )
    return tuple(unknowns)


def build_behaviour(
    features: CustomerFeatures,
    episodes: tuple[TravelEpisode, ...] = (),
) -> CustomerBehaviour:
    validate_as_of(features.as_of)
    traits = assign_traits(features, episodes)
    return CustomerBehaviour(
        customer_id=features.customer_id,
        customer_ref=features.customer_ref,
        as_of=features.as_of,
        computed_at=datetime.now(tz=UTC),
        traits=traits,
        unknowns=_unknowns(features, traits),
    )


class BehaviourService:
    def __init__(
        self,
        features: CustomerFeatureService | FeatureCalculator,
        memory: EventMemoryService | EpisodeRecaller,
    ) -> None:
        self.features = features
        self.memory = memory

    async def evaluate(self, customer_ref: str, as_of: datetime) -> CustomerBehaviour:
        validate_as_of(as_of)
        features = await self.features.calculate(customer_ref, as_of)
        recalled = await self.memory.recall(customer_ref, as_of)
        episodes = tuple(getattr(recalled, "historical_episodes", ()))
        return build_behaviour(features, episodes)
