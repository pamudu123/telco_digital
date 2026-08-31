from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from telco_digital.domain.entities import Recharge

SMALL_RECHARGE_THRESHOLD = Decimal("150")
MIN_SMALL_RECHARGE_COUNT = 5
LOOKBACK = timedelta(days=30)


def small_recharges_in_window(
    recharges: list[Recharge],
    *,
    as_of: datetime,
    threshold: Decimal = SMALL_RECHARGE_THRESHOLD,
    lookback: timedelta = LOOKBACK,
) -> list[Recharge]:
    """Return the exact observations used by the small-recharge rule."""
    window_start = as_of - lookback
    return [
        recharge
        for recharge in recharges
        if window_start <= recharge.occurred_at <= as_of and recharge.amount <= threshold
    ]


def frequent_small_recharge_pattern(
    recharges: list[Recharge],
    *,
    as_of: datetime,
    threshold: Decimal = SMALL_RECHARGE_THRESHOLD,
    min_count: int = MIN_SMALL_RECHARGE_COUNT,
    lookback: timedelta = LOOKBACK,
) -> bool:
    """True when many small top-ups occur in the lookback window ending at as_of."""
    recent = small_recharges_in_window(
        recharges,
        as_of=as_of,
        threshold=threshold,
        lookback=lookback,
    )
    return len(recent) >= min_count
