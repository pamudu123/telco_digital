# Capability 10 — Decision engine and explanations

## 1. POC objective

Prove that ranked offers, behaviour traits and a churn score can be composed
into a next-best action with reason codes. A high churn probability must not
become a discount or an invented plan.

## 2. Demonstrated scenario

U001 queried for Singapore with unknown duration is `PRESENT_OFFER` for
`ROAM_15` (`HISTORICAL_EPISODE`, `CATALOGUE_MATCH`, `DURATION_UNKNOWN`).
U004 HIGH churn with declining engagement or open network/complaint tickets is
`SUPPORT_FOLLOW_UP` (`CHURN_HIGH`, `NETWORK_OR_COMPLAINT`, `NO_AUTO_DISCOUNT`).
U002 `PRICE_SENSITIVE` with no travel catalogue context is `NO_INVENTED_OFFER`.
A destination-unknown query without price-sensitivity is `REQUEST_INFORMATION`.

## 3. Data inputs and outputs

Inputs are capability-03/04/05/06 documents only. Missing fraud, forecast and
twin values are listed as unknowns. The output is a typed
`customer-decision-v1` document: action, optional catalogue target, reason
codes, confidence and `{what, why, evidence, confidence, unknowns, alternatives}`.
Decisions are derived and not persisted. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`RecommendationService + BehaviourService + ChurnService -> DecisionEngine`

Rules stay in `decisioning/`. No new SQL or Cypher is added. Churn is a
constraint that can block an upsell; it never generates a SKU.

## 5. Public services and types

- `DecisionEngine.evaluate(customer_ref, as_of, destination=None)`
- `decide(recommendation, behaviour, churn)`
- `CustomerDecision`, `DecisionAction`, `DecisionExplanation`

Actions: `PRESENT_OFFER`, `SUPPORT_FOLLOW_UP`, `REQUEST_INFORMATION`,
`NO_INVENTED_OFFER`.

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is `notebooks/10_decisioning/10_decisioning.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/10_decisioning/10_decisioning.ipynb
```

The notebook reconstructs seed facts in memory, compares U001 / U002 / U004
and writes compact tables. Runtime services stay in `src/telco_digital`.
There is no sklearn.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/10_decisioning/outputs/`:

- `metrics.json`
- `tables/persona_decisions.json`
- `tables/u004_no_discount.json`
- `plots/decision_actions.png`

These are POC evidence over synthetic fixtures, not estimates of take-up.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_decisioning.py tests/scenarios/scenario_decision.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check src/telco_digital/decisioning tests/unit/test_decisioning.py
```

Read live results at
`/api/v1/customers/U001/decision?as_of=2026-08-20T12:00:00Z&destination=SG`.

## 9. What is implemented

- Composition of event memory, behaviour, churn and catalogue recommendations.
- Deterministic NBA with reason codes and What / Why / alternatives.
- High churn blocks upsell and never invents a 20% discount.
- Read-only API plus Journey, Customer 360 and Models decision panels.

## 10. What is not implemented

Outcome recording, fraud scoring, retailer forecast, digital twins and command
writes are not implemented. FastAPI-complete and the simulator stay not started.

## 11. POC limitations

Rules are persona-shaped. Missing 07–09 inputs are explicit unknowns, not
zeros. The catalogue and journeys are synthetic.

## 12. Production improvements that would be required later

Approve constraint owners, record suggestion / choice / outcome, evaluate
actions against labelled results, and only then add learned ranking that still
cannot invent catalogue codes.

## 13. Dependency for the next capability

Capability 11 presents these explanations in Copilot. See
[11-copilot.md](./11-copilot.md).
