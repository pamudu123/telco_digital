# Capability 04 — Behaviour intelligence

## 1. POC objective

Prove that reusable customer traits can be derived at an explicit `as_of` from
capability-02 features and capability-03 travel episodes, with confidence and
evidence on every trait.

## 2. Demonstrated scenario

U002's repeated small recharges yield `PRICE_SENSITIVE`. U001's March Singapore
history yields `FREQUENT_TRAVELLER` and `HEAVY_DATA_USER`. No trait is invented
when evidence is missing. Clustering of feature vectors is a notebook
experiment only.

## 3. Data inputs and outputs

Inputs are versioned `customer-features-v1` documents and derived travel
episodes. The output is a typed `customer-behaviour-v1` document containing
traits, confidence, evidence, provenance and explicit unknowns. Traits are
derived and not persisted. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`CustomerFeatureService + EventMemoryService -> BehaviourService`

Rules stay in `intelligence/behaviour`. No new SQL is added. The API does not
load a clustering model.

## 5. Public services and types

- `BehaviourService.evaluate(customer_ref, as_of)`
- `assign_traits`, `build_behaviour`
- `CustomerBehaviour`, `BehaviourTrait`

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is `notebooks/04_behaviour/04_behaviour.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/04_behaviour/04_behaviour.ipynb
```

The notebook is the experiment surface. It reconstructs seed facts in memory,
assigns rule traits, runs k-means against persona labels, and writes compact
tables and plots. Runtime services stay in `src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/04_behaviour/outputs/`:

- `metrics.json`
- `tables/u002_price_sensitive.json`
- `tables/golden_traits.json`
- `tables/cluster_vs_persona.json`
- `plots/trait_counts.png`
- `plots/cluster_vs_persona.png`

These are POC evidence over synthetic fixtures, not estimates of a real
population.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_behaviour.py tests/scenarios/scenario_behaviour.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check .
```

Read live results at
`/api/v1/customers/U002/behaviour?as_of=2026-08-21T00:00:00Z`.

## 9. What is implemented

- Point-in-time rule traits with confidence and evidence.
- Use of temporal features and travel episodes as inputs.
- Read-only behaviour API and Customer 360 trait panel.
- Notebook clustering compared to generator personas.

## 10. What is not implemented

A persisted trait store, online clustering in the API, churn prediction,
recommendations, twins and Copilot are not implemented.

## 11. POC limitations

Trait thresholds are demonstrative. The journeys are synthetic. Clustering in
the notebook does not become a served model and does not establish real-world
segment quality.

## 12. Production improvements that would be required later

Approve trait definitions with domain owners, evaluate rules against labelled
history, introduce governed lineage, and only then consider a versioned trait
store or a served clustering model.

## 13. Dependency for the next capability

Capability 05 may consume declining-engagement traits and the same feature
windows as churn inputs. It remains not started and no churn score is included
here.
