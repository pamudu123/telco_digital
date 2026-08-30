from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from telco_digital.domain.entities import Recharge
from telco_digital.domain.rules.recharge import frequent_small_recharge_pattern


def test_five_small_recharges_match_pattern() -> None:
    customer_id = uuid4()
    account_id = uuid4()
    as_of = datetime.fromisoformat("2026-08-20T10:00:00+00:00")
    recharges = [
        Recharge(
            customer_id=customer_id,
            account_id=account_id,
            amount=Decimal("100"),
            currency="LKR",
            occurred_at=as_of - timedelta(days=offset),
        )
        for offset in (16, 12, 8, 4, 0)
    ]
    assert frequent_small_recharge_pattern(recharges, as_of=as_of)


def test_large_recharges_do_not_match() -> None:
    customer_id = uuid4()
    account_id = uuid4()
    as_of = datetime.fromisoformat("2026-08-20T10:00:00+00:00")
    recharges = [
        Recharge(
            customer_id=customer_id,
            account_id=account_id,
            amount=Decimal("2000"),
            currency="LKR",
            occurred_at=as_of - timedelta(days=i),
        )
        for i in range(5)
    ]
    assert not frequent_small_recharge_pattern(recharges, as_of=as_of)
