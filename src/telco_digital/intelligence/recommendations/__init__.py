"""Candidate generation from the real catalogue only (Milestone 7)."""

from telco_digital.intelligence.recommendations.catalogue import (
    CataloguePlan,
    PlanRepositoryCatalogue,
)
from telco_digital.intelligence.recommendations.service import (
    RECOMMENDATION_SET_VERSION,
    CustomerRecommendation,
    DecisionMode,
    RankedOffer,
    RecommendationService,
    UncertaintyFact,
    assess_uncertainty,
    build_recommendation,
    decide_mode,
    generate_candidates,
    score_offer,
)

__all__ = [
    "RECOMMENDATION_SET_VERSION",
    "CataloguePlan",
    "CustomerRecommendation",
    "DecisionMode",
    "PlanRepositoryCatalogue",
    "RankedOffer",
    "RecommendationService",
    "UncertaintyFact",
    "assess_uncertainty",
    "build_recommendation",
    "decide_mode",
    "generate_candidates",
    "score_offer",
]
