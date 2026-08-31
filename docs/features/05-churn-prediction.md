# Capability 05 — Churn prediction

## 1. POC objective

Prove that a supervised churn model can be trained in a notebook on a synthetic
labelled population, then used at an explicit `as_of` to return probability,
risk band, drivers, model version and a feature snapshot.

## 2. Demonstrated scenario

U004's falling August usage, missing recent recharge, open `NETWORK_ISSUE` and
open `COMPLAINT` score **HIGH** churn risk from the served logistic regression.
U003 remains **LOW**. Drivers are coefficient contributions, not invented text.

## 3. Data inputs and outputs

Inputs are versioned `customer-features-v1` windows: usage and recharge trends,
service/complaint volume, campaign and loyalty engagement, and plan/travel
counts. Tenure days are not on that contract and are listed as unknown. The
output is a typed `customer-churn-v1` document. Predictions are derived and not
persisted. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`CustomerFeatureService -> vector_from_features -> notebook-trained artifact -> ChurnService`

Training stays in `notebooks/05_churn`. The notebook compares logistic
regression with gradient-boosted trees and exports coefficients plus scaler
parameters. Runtime scoring applies that artifact and does not import sklearn.

## 5. Public services and types

- `ChurnService.predict(customer_ref, as_of)`
- `score_churn`, `vector_from_features`, `predict_probability`
- `CustomerChurn`, `ChurnDriver`

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is `notebooks/05_churn/05_churn.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/05_churn/05_churn.ipynb
```

The notebook is the training surface. It builds a synthetic labelled frame,
fits both candidate models, writes compact tables and plots, and exports
`churn-model-v1.json` for the API. Runtime services stay in `src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/05_churn/outputs/`:

- `metrics.json`
- `tables/model_comparison.json`
- `tables/golden_scores.json`
- `tables/lr_coefficients.json`
- `plots/model_comparison.png`
- `plots/lr_coefficients.png`
- `plots/risk_bands.png`

The served artifact is `notebooks/05_churn/artifacts/churn-model-v1.json`.
These are POC evidence over synthetic labels, not estimates of a real
population.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_churn.py tests/scenarios/scenario_churn.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check .
```

Read live results at
`/api/v1/customers/U004/churn?as_of=2026-08-21T00:00:00Z`.

## 9. What is implemented

- Notebook training of logistic regression versus gradient-boosted trees.
- A served logistic-regression artifact with versioned features and bands.
- Point-in-time probability, risk band, drivers and feature snapshot.
- Read-only churn API and Customer 360 prediction panel.

## 10. What is not implemented

A persisted prediction store, online retraining, gradient-boosting in the API,
next-best action, recommendations, twins and Copilot are not implemented.

## 11. POC limitations

Labels are persona-shaped synthetic outcomes. The journeys are synthetic. Hold-out
metrics do not establish real-world churn accuracy or production calibration.

## 12. Production improvements that would be required later

Approve an outcome definition with domain owners, train on labelled history,
add tenure and plan-change features to the shared contract, introduce governed
lineage, monitoring and drift checks, and only then persist prediction records.

## 13. Dependency for the next capability

Capability 06 ranks catalogue offers from travel memory and does not turn a
HIGH band into a discount. See
[06-recommendations-uncertainty.md](./06-recommendations-uncertainty.md).
