# Capability 09 — Digital twins

## 1. POC objective

Prove that a Digital Twin is a **computed** view of observed facts, recent
change, historical episodes, graph context, inferred traits, predictions,
unknowns, recommendations and warnings at an explicit `as_of`. It is not
another authoritative table. Retailer twins are first-class.

## 2. Demonstrated scenario

U001 queried for Singapore after the March 2026 trip is assembled into a
customer twin: Observed country and plan, Recent 30-day windows, Historical
March episode (6 days / 11.4 GB / `ROAM_15`), Inferred
`FREQUENT_TRAVELLER` and `HEAVY_DATA_USER`, Predicted churn from the served
artifact, Recommended `SCENARIO_BASED` `ROAM_15`, and explicit unknowns for
trip duration, fraud and demand. RET-001 exposes Observed and Historical
sales/inventory; Predicted and Recommended stay unknown because capabilities
07 and 08 are not started.

## 3. Data inputs and outputs

Inputs are capability-02 features, capability-03 `CustomerContext`,
capability-04 traits, capability-05 churn, capability-06 catalogue offers and
point-in-time `ObservedCustomerState`. The output is a typed
`digital-twin-v1` document. Twins are derived and not persisted. PostgreSQL
remains authoritative. `CustomerContext` is embedded, not replaced.

## 4. Architecture and data flow

```
ObservedCustomerState
CustomerFeatureService
EventMemoryService
Behaviour rules
Churn artifact
RecommendationService
        ↓
DigitalTwinService.build(entity_id, as_of)
        ↓
CustomerDigitalTwin | RetailerDigitalTwin
```

Assembly stays in `intelligence/digital_twin`. SQL stays in existing
repositories. No twin row is written.

## 5. Public services and types

- `DigitalTwinService.build(entity_id, as_of, destination=None)`
- `build_customer`, `build_retailer`
- `assemble_customer_twin`, `assemble_retailer_twin`
- `CustomerDigitalTwin`, `RetailerDigitalTwin`

Customer sections: Observed, Recent, Historical, Relationships, Inferred,
Predicted, Unknown, Recommended, Warnings.

Retailer sections: Observed, Historical, Predicted, Recommended.

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is
`notebooks/09_digital_twins/09_digital_twins.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/09_digital_twins/09_digital_twins.ipynb
```

The notebook reconstructs seed facts in memory, assembles customer and
retailer twins and writes compact tables and plots. Runtime services stay in
`src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/09_digital_twins/outputs/`:

- `metrics.json`
- `tables/u001_twin.json`
- `tables/section_coverage.json`
- `tables/retailer_twin.json`
- `plots/section_coverage.png`
- `plots/predicted_vs_recommended.png`

These are POC evidence over synthetic fixtures, not estimates of twin quality
in production.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_digital_twin.py tests/scenarios/scenario_digital_twin.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check src/telco_digital/intelligence/digital_twin tests/unit/test_digital_twin.py
```

Read live results at
`/api/v1/customers/U001/twin?as_of=2026-08-20T12:00:00Z&destination=SG` and
`/api/v1/showcase/sfa/retailers/RET-001/twin`.

## 9. What is implemented

- Computed customer twin composing capabilities 02–06 plus observed state.
- First-class retailer twin from recorded sales and inventory facts.
- Explicit unknown slots for fraud, demand and the decision engine.
- Read-only twin API plus Customer 360 and Retail panels.

## 10. What is not implemented

A persisted twin store, graph-fraud scores, SFA forecasts, next-best action
and Copilot narration over the twin are not implemented.

## 11. POC limitations

Twins are demonstrative over synthetic seed journeys. Graph relationships
are unknown when Neo4j is unavailable. Capabilities 07 and 08 remain not
started, so Predicted fraud/demand stay unknown by design.

## 12. Production improvements that would be required later

Version twin contracts with domain owners, add fraud and forecast sections
only after those capabilities exist, record which twin snapshot a decision
used, and never treat a twin as a writeable customer record.

## 13. Dependency for the next capability

Capability 10 may later turn twin Predicted + Recommended into a next-best
action with reason codes. Capability 11 may narrate the same twin. Both
remain not started.
