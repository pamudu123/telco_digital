from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from telco_digital.api.deps import parse_as_of
from telco_digital.application.demo_dataset import (
    DATASET_VERSION,
    END_AT,
    START_AT,
    expected_generated_row_count,
    persona_for_ref,
)
from telco_digital.application.queries.showcase import OverviewCounts, display_persona


def test_persona_mapping_uses_documented_refs() -> None:
    assert persona_for_ref("U001") == "FREQUENT_TRAVELLER"
    assert persona_for_ref("U006") == "PROMOTION_RESPONSIVE"
    assert persona_for_ref("U007") == "UNKNOWN_DURATION_TRAVELLER"
    assert persona_for_ref("BG0001") == "FREQUENT_TRAVELLER"
    assert persona_for_ref("unknown") is None


def test_expected_generated_rows_are_not_a_full_table_sum() -> None:
    generated = expected_generated_row_count(background_customers=7)
    assert generated > 0
    assert generated == expected_generated_row_count(background_customers=7)


def test_overview_dto_requires_explicit_source() -> None:
    now = datetime.now(tz=UTC)
    counts = OverviewCounts(
        source="live_database",
        as_of=END_AT,
        dataset_version=DATASET_VERSION,
        queried_at=now,
        generated_rows=10,
        total_database_rows=25,
        total_customers=12,
        background_customers=7,
        golden_personas=10,
        activity_events=4,
        outbox_events=4,
        event_outbox_parity=True,
        period_start=START_AT,
        period_end=END_AT,
        generated_row_counts={"customers": 12},
        domain_coverage=(),
    )
    payload = counts.model_dump(mode="json")
    assert payload["source"] == "live_database"
    assert payload["generated_rows"] != payload["total_database_rows"]
    assert "unavailable" != payload["source"]


def test_parse_as_of_rejects_invalid_and_naive_values() -> None:
    assert parse_as_of(None) == END_AT
    with pytest.raises(HTTPException) as invalid:
        parse_as_of("not-a-date")
    assert invalid.value.status_code == 422
    with pytest.raises(HTTPException) as naive:
        parse_as_of("2026-08-31T23:59:00")
    assert naive.value.status_code == 422


def test_display_persona_title_cases_codes() -> None:
    assert display_persona("FREQUENT_TRAVELLER") == "Frequent Traveller"
