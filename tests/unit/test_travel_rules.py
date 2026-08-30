from datetime import datetime, timedelta
from uuid import uuid4

from telco_digital.domain.entities import Travel
from telco_digital.domain.rules.travel import is_impossible_travel, location_at, min_transit_hours
from telco_digital.domain.value_objects import normalize_country


def test_country_aliases() -> None:
    assert normalize_country("Singapore") == "SG"
    assert normalize_country("USA") == "US"
    assert normalize_country("Sri Lanka") == "LK"


def test_singapore_usa_one_hour_is_impossible() -> None:
    start = datetime.fromisoformat("2026-08-26T09:00:00+00:00")
    end = datetime.fromisoformat("2026-08-26T10:00:00+00:00")
    assert min_transit_hours("SG", "US") >= 18
    assert is_impossible_travel(
        from_country="Singapore",
        from_time=start,
        to_country="USA",
        to_time=end,
    )


def test_same_country_is_not_impossible() -> None:
    t = datetime.fromisoformat("2026-08-26T09:00:00+00:00")
    assert not is_impossible_travel(
        from_country="SG", from_time=t, to_country="Singapore", to_time=t + timedelta(hours=1)
    )


def test_location_prefers_open_travel() -> None:
    as_of = datetime.fromisoformat("2026-08-26T10:00:00+00:00")
    travel = Travel(
        customer_id=uuid4(),
        country_code="SG",
        started_at=datetime.fromisoformat("2026-08-26T09:00:00+00:00"),
    )
    loc = location_at(home_country="LK", travels=[travel], as_of=as_of)
    assert loc.country_code == "SG"
    assert loc.source == "travel"
    assert loc.travel is not None
    assert not loc.travel.duration_known
