from datetime import datetime
from uuid import uuid4

import pytest

from telco_digital.intelligence.event_memory import (
    CustomerContext,
    EpisodeMatch,
    MatchRank,
    TravelEpisode,
    TravelSituation,
)
from telco_digital.intelligence.recommendations import (
    RECOMMENDATION_SET_VERSION,
    CataloguePlan,
    DecisionMode,
    RecommendationService,
    build_recommendation,
    generate_candidates,
)

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")

CATALOGUE = (
    CataloguePlan(
        plan_code="PLAN_A",
        name="Local Data A",
        plan_type="LOCAL",
        data_mb=10240,
        validity_days=30,
        price=300,
        currency="LKR",
    ),
    CataloguePlan(
        plan_code="ROAM_5",
        name="Roaming 5GB",
        plan_type="ROAMING",
        data_mb=5120,
        validity_days=5,
        price=150,
        currency="LKR",
        country_code="SG",
    ),
    CataloguePlan(
        plan_code="ROAM_15",
        name="Roaming 15GB",
        plan_type="ROAMING",
        data_mb=15360,
        validity_days=15,
        price=350,
        currency="LKR",
        country_code="SG",
    ),
    CataloguePlan(
        plan_code="ROAM_30",
        name="Roaming 30GB",
        plan_type="ROAMING",
        data_mb=30720,
        validity_days=30,
        price=600,
        currency="LKR",
        country_code="SG",
    ),
    CataloguePlan(
        plan_code="FAKE_PLAN",
        name="Invented",
        plan_type="ROAMING",
        data_mb=99999,
        validity_days=99,
        price=1,
        currency="LKR",
        country_code="SG",
        active=False,
    ),
)


def _episode() -> TravelEpisode:
    return TravelEpisode(
        customer_id=uuid4(),
        customer_ref="U001",
        travel_id=uuid4(),
        destination="SG",
        destination_name="Singapore",
        start_at=datetime.fromisoformat("2026-03-10T08:00:00+00:00"),
        end_at=datetime.fromisoformat("2026-03-16T18:00:00+00:00"),
        duration_days=6,
        duration_known=True,
        context={"destination": "SG"},
        actions={"plan_selected": "ROAM_15"},
        outcome="No additional package required",
        metrics={"usage_gb": 11.4, "usage_mb": 11400.0, "duration_days": 6},
    )


def _context(situation: TravelSituation) -> CustomerContext:
    episode = _episode()
    return CustomerContext(
        customer_id=episode.customer_id,
        customer_ref="U001",
        as_of=AS_OF,
        computed_at=AS_OF,
        current_situation=situation,
        historical_episodes=(episode,),
        matches=(
            EpisodeMatch(
                episode=episode,
                rank=MatchRank.SAME_CUSTOMER_SAME_SITUATION,
                similarity=0.9,
                reasons=("Same destination",),
            ),
        ),
    )


def test_unknown_duration_is_scenario_based_and_ranks_roam_15() -> None:
    document = build_recommendation(
        _context(
            TravelSituation(
                destination="SG",
                destination_name="Singapore",
                destination_known=True,
                duration_known=False,
                source="query",
            )
        ),
        CATALOGUE,
    )
    assert document.mode == DecisionMode.SCENARIO_BASED
    assert document.primary is not None
    assert document.primary.plan_code == "ROAM_15"
    codes = [item.plan_code for item in document.ranked]
    assert codes[0] == "ROAM_15"
    assert "ROAM_5" in codes
    assert "ROAM_30" in codes
    assert "FAKE_PLAN" not in codes
    assert "PLAN_A" not in codes
    assert document.recommendation_set_version == RECOMMENDATION_SET_VERSION
    statuses = {item.name: item.status for item in document.uncertainty}
    assert statuses["destination"] == "known"
    assert statuses["trip_duration"] == "unknown"
    assert statuses["historical_plan"] == "inferred"


def test_known_six_day_duration_keeps_roam_15_first() -> None:
    document = build_recommendation(
        _context(
            TravelSituation(
                destination="SG",
                destination_name="Singapore",
                destination_known=True,
                duration_known=True,
                duration_days=6,
                source="travel",
            )
        ),
        CATALOGUE,
    )
    assert document.primary is not None
    assert document.primary.plan_code == "ROAM_15"
    assert document.mode in {
        DecisionMode.SINGLE_RECOMMENDATION,
        DecisionMode.RANKED_OPTIONS,
    }


def test_missing_destination_asks_for_information() -> None:
    document = build_recommendation(
        CustomerContext(
            customer_id=uuid4(),
            customer_ref="U003",
            as_of=AS_OF,
            computed_at=AS_OF,
            current_situation=TravelSituation(source="none"),
            historical_episodes=(),
            matches=(),
        ),
        CATALOGUE,
    )
    assert document.mode == DecisionMode.ASK_FOR_INFORMATION
    assert document.ranked == ()
    assert document.primary is None


def test_unknown_destination_catalogue_does_not_invent_a_plan() -> None:
    document = build_recommendation(
        CustomerContext(
            customer_id=uuid4(),
            customer_ref="U001",
            as_of=AS_OF,
            computed_at=AS_OF,
            current_situation=TravelSituation(
                destination="US",
                destination_name="United States",
                destination_known=True,
                duration_known=False,
                source="query",
            ),
            historical_episodes=(),
            matches=(),
        ),
        CATALOGUE,
    )
    assert document.mode == DecisionMode.NO_RECOMMENDATION
    assert document.ranked == ()
    assert any(
        "invented" in item.lower() or "catalogue" in item.lower() for item in document.unknowns
    )


def test_generate_candidates_never_includes_inactive_or_local() -> None:
    offers = generate_candidates(CATALOGUE, destination="SG")
    codes = {item.plan_code for item in offers}
    assert codes == {"ROAM_5", "ROAM_15", "ROAM_30"}


def test_naive_as_of_is_rejected() -> None:
    context = _context(TravelSituation(destination="SG", destination_known=True, source="query"))
    context = context.model_copy(update={"as_of": datetime(2026, 8, 20, 12)})
    with pytest.raises(ValueError, match="timezone-aware"):
        build_recommendation(context, CATALOGUE)


@pytest.mark.asyncio
async def test_service_uses_memory_and_catalogue() -> None:
    context = _context(
        TravelSituation(
            destination="SG",
            destination_name="Singapore",
            destination_known=True,
            duration_known=False,
            source="query",
        )
    )

    class Memory:
        async def recall(self, customer_ref: str, as_of: datetime, *, destination=None):
            return context

    class Catalogue:
        async def list_roaming(self, *, country_code: str | None):
            assert country_code == "SG"
            return CATALOGUE

    result = await RecommendationService(Memory(), Catalogue()).recommend(
        "U001", AS_OF, destination="SG"
    )
    assert result.primary is not None
    assert result.primary.plan_code == "ROAM_15"
    assert result.mode == DecisionMode.SCENARIO_BASED
