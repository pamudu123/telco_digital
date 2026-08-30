# Milestones (locked)

Do not skip Milestone 1. Do not connect an LLM until Milestone 12.

## Milestone 1 — Core relational foundation

Build: PostgreSQL, SQLAlchemy, Alembic, `core.customer`, `core.account`, `core.device`, `core.plan`, `core.subscription`, `telco.recharge`, `telco.usage_event`, `telco.travel`, `activity.event`, `integration.outbox_event`.

Success:

- Can create customer
- Can recharge
- Can purchase plan
- Can record data usage
- Can record travel
- Can reconstruct state at any timestamp

**Do not proceed until this works.**

## Milestone 2 — Temporal simulator foundation

Build: `CustomerStateService`, `TimelineService`, `TemporalFeatureService`, `WarningService`.

Tests:

- U001 09:00 Singapore then 10:00 USA → `IMPOSSIBLE_TRAVEL`
- Repeated 100 top-ups → `FREQUENT_SMALL_RECHARGE_PATTERN`

## Milestone 3 — Neo4j

Outbox worker, graph projector, Customer / Device / Wallet / Merchant nodes and relationships.

Test: U001 and U002 share D001. Rebuild the graph from Postgres from scratch. If rebuild works, architecture is correct.

## Milestone 4 — Feature layer

`TemporalFeatureService` + `GraphFeatureService` for `customer + as_of` → recent / historical / graph features.

## Milestone 5 — Event memory

Travel episodes first. March Singapore trip retrieved when August Singapore trip occurs: duration, usage, plan, outcome, similarity.

## Milestone 6 — Behaviour + churn

Synthetic population (1,000–5,000) with personas. Train behaviour clustering and a churn classifier (logistic regression vs gradient boosted trees). Evaluate properly.

## Milestone 7 — Recommendation

`CandidateGenerator`, `CandidateScorer`, `EventMemoryMatcher`, `UncertaintyEvaluator`, `RecommendationService`.

- Singapore, duration unknown → `SCENARIO_BASED`
- Singapore, 6-day previous trip exists → `ROAM_15` ranked highest

AI must never invent a plan that does not exist.

## Milestone 8 — Fraud

`FraudRuleService`, graph fraud features, `FraudScorer`. Seed one fraud cluster. Show transaction-only risk vs transaction + graph risk.

Start with deterministic rules (shared device, known fraud within 2 hops, wallet funnel, circular transfers, abnormal creation). Then add graph ML features.

## Milestone 9 — SFA

Retailers, sales, inventory, promotions. Naive baseline and moving average before gradient boosting. Forecast → stockout probability → SFA action.

## Milestone 10 — Digital Twins

Customer twin: Observed, Recent, Historical, Graph, Inferred, Predicted, Unknown, Recommended, Warnings.  
Retailer twin: Observed, Historical, Predicted, Recommended.

Twins are **computed** (`DigitalTwinService.build(entity_id, as_of)`), not another authoritative table.

## Milestone 11 — Decision Engine

Rules, candidate ranking, uncertainty, NBA, explanation. Predictions do not become discounts by themselves.

## Milestone 12 — Copilot

LLM is a presentation layer over Digital Twin, predictions, recommendations, warnings, graph evidence, and historical episodes.

## Milestone 13 — APIs

Expose stable application services. Do not design the system around route names.

Services to wrap later: `RecordRecharge`, `RecordTravel`, `PurchasePlan`, `GetCustomerState`, `GetTimeline`, `BuildCustomerTwin`, `EvaluateChurn`, `GenerateRecommendations`, `EvaluateFraud`, `ForecastRetailerDemand`.

## Milestone 14 — UI simulator

Select user → date/time → action → submit → Postgres write → event → outbox → Neo4j → features → twin → warnings → predictions → recommendation → explanation.

## Milestone 15 — Supabase deployment

Local Postgres → Supabase Postgres. Domain architecture does not change. Configure env, pooling, migrations, secrets, RLS if exposed, backups, logging. Deploy Neo4j separately.

When exposing frontend-accessible tables, use explicit grants plus RLS and a dedicated API schema. Verify current Supabase database and API configuration at deploy time rather than assuming older defaults.
