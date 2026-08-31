# Capability 06 — Recommendations and uncertainty

## 1. POC objective

Prove that a travel situation can be turned into ranked catalogue offers with
an explicit decision mode and known / inferred / predicted / unknown facts.
The platform must never invent a plan that is not in the catalogue.

## 2. Demonstrated scenario

U001 queried for Singapore after the March 2026 trip (6 days, 11.4 GB,
`ROAM_15`) is `SCENARIO_BASED` because duration is unknown. `ROAM_15` ranks
highest. `ROAM_5` (1–3 days) and `ROAM_30` (8–14 days) remain alternatives
from the real catalogue.

## 3. Data inputs and outputs

Inputs are capability-03 `CustomerContext` and active `ROAMING` catalogue
rows. The output is a typed `customer-recommendations-v1` document containing
mode, ranked offers, uncertainty facts and unknowns. Recommendations are
derived and not persisted. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`EventMemoryService + PlanRepositoryCatalogue -> RecommendationService`

Candidate generation, scoring and uncertainty stay in
`intelligence/recommendations`. SQL stays in the existing plan repository.
Scoring is deterministic. There is no `model → plan` mapping.

## 5. Public services and types

- `RecommendationService.recommend(customer_ref, as_of, destination=None)`
- `generate_candidates`, `score_offer`, `decide_mode`, `assess_uncertainty`,
  `build_recommendation`
- `CustomerRecommendation`, `RankedOffer`, `UncertaintyFact`, `DecisionMode`

Modes: `SINGLE_RECOMMENDATION`, `RANKED_OPTIONS`, `SCENARIO_BASED`,
`ASK_FOR_INFORMATION`, `NO_RECOMMENDATION`.

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is
`notebooks/06_recommendations/06_recommendations.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/06_recommendations/06_recommendations.ipynb
```

The notebook reconstructs seed facts in memory, ranks the Singapore catalogue
and writes compact tables and plots. Runtime services stay in
`src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/06_recommendations/outputs/`:

- `metrics.json`
- `tables/u001_ranked.json`
- `tables/decision_modes.json`
- `tables/invented_plan_rejected.json`
- `plots/candidate_scores.png`
- `plots/uncertainty_status.png`

These are POC evidence over synthetic fixtures, not estimates of offer take-up.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_recommendations.py tests/scenarios/scenario_travel_recommendation.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check src/telco_digital/intelligence/recommendations tests/unit/test_recommendations.py
```

Read live results at
`/api/v1/customers/U001/recommendations?as_of=2026-08-20T12:00:00Z&destination=SG`.

## 9. What is implemented

- Catalogue-only candidate generation for roaming offers.
- Deterministic ranking from retrieved travel episodes.
- Decision modes including `SCENARIO_BASED` when duration is unknown.
- Uncertainty facts with known / inferred / unknown statuses.
- Read-only API plus Journey and Customer 360 recommendation panels.

## 10. What is not implemented

Outcome recording, a persisted recommendation store, a learned ranker, churn
discounts, digital twins, the decision engine and Copilot are not implemented.

## 11. POC limitations

Scenario bands are demonstrative. The catalogue and journeys are synthetic.
Hold-out offer quality is not estimated. Churn is not applied as an offer rule.

## 12. Production improvements that would be required later

Approve offer constraints with domain owners, record suggestion / choice /
outcome, evaluate ranking against labelled take-up, and only then consider a
learned scorer that still cannot invent catalogue codes.

## 13. Dependency for the next capability

Capability 07 is graph fraud and does not consume these offers. Capability 10
may later turn a ranked offer plus churn into a next-best action. Both remain
not started.
