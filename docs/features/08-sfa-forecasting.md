# Capability 08 — SFA forecasting

## 1. POC objective

Prove that retailer demand can be forecast at an explicit `as_of` from
authoritative SFA sales and inventory facts, then turned into a stockout
warning and a restock action. Naive and moving-average baselines are compared
with ARIMA and Facebook Prophet before a winner is served.

## 2. Demonstrated scenario

RET-001 / `POC-PROD-01` at `2026-08-21T00:00:00Z` has about **18 units** on
hand and a **7-day forecast near 47**. Cover is below one week, so the score
is **HIGH** `STOCKOUT_RISK` with action **RESTOCK**. A stable retailer such as
RET-003 remains **HOLD**.

## 3. Data inputs and outputs

Inputs are capability-00 `sfa.sale` and `sfa.inventory_event` rows. Monthly
pulses are expanded onto a derived daily demand path with weekly seasonality
and the documented RET-001 late-period surge. The output is a typed
`retailer-forecast-v1` document. Forecasts are derived and not persisted.
PostgreSQL remains authoritative.

## 4. Architecture and data flow

`PostgreSQL sfa facts -> PostgresRetailerDemandQueries -> daily expansion -> notebook-trained artifact -> ForecastingService`

Training stays in `notebooks/08_sfa_forecasting`. The notebook fits naive,
seasonal-naive, moving-average, ARIMA/SARIMAX and Prophet models, then exports
the winner. Runtime scoring reconstructs that artifact in numpy and does not
import Prophet or statsmodels.

## 5. Public services and types

- `ForecastingService.forecast(retailer_ref, as_of, horizon_days=7)`
- `score_forecast`, `forecast_from_generated`, `forecast_from_history`
- `RetailerForecast`, `ProductForecast`

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is `notebooks/08_sfa_forecasting/08_sfa_forecasting.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/08_sfa_forecasting/08_sfa_forecasting.ipynb
```

The notebook is the training surface. It builds the daily panel, fits the
candidate models, writes compact tables and plots, and exports
`sfa-forecast-v1.json` for the API. Runtime services stay in `src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/08_sfa_forecasting/outputs/`:

- `metrics.json`
- `tables/model_comparison.json`
- `tables/hero_forecast.json`
- `tables/reconstruction.json`
- `plots/model_comparison.png`
- `plots/hero_forecast.png`
- `plots/stockout_cover.png`

The served artifact is `notebooks/08_sfa_forecasting/artifacts/sfa-forecast-v1.json`.
These are POC evidence over a synthetic SFA panel, not estimates of a live
retail network.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_forecasting.py tests/scenarios/scenario_retailer_stockout.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check .
```

Read live results at
`/api/v1/showcase/sfa/retailers/RET-001/forecast?as_of=2026-08-21T00:00:00Z`.

## 9. What is implemented

- Notebook training of naive, moving-average, ARIMA and Prophet models.
- A served artifact with versioned daily demand, 7-day forecast and cover.
- Point-in-time stockout probability, risk band and RESTOCK / MONITOR / HOLD.
- Read-only forecast API and Retail and SFA forecast panel.

## 10. What is not implemented

A persisted prediction store, online retraining, a retailer digital twin, the
decision engine, graph fraud and Copilot are not implemented.

## 11. POC limitations

Daily demand is a derived expansion of monthly pulses. Labels are
scenario-shaped. Hold-out MAPE does not establish real-world forecast accuracy
or production calibration. Supplier lead time and promotions are unknown.

## 12. Production improvements that would be required later

Approve a daily POS contract, train on labelled sell-through, add promotions
and lead times, introduce monitoring and drift checks, and only then persist
forecast records for visit planning.

## 13. Dependency for the next capability

Capability 09 may consume these forecasts on a retailer twin. Capability 07
(graph fraud) does not consume them. Both remain not started.
