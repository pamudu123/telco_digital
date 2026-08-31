# Capability 08 SFA forecasting

This executed POC notebook trains naive, moving-average, ARIMA and Facebook
Prophet models on a deterministic daily retailer-demand panel. It retains
compact tables, plots and the served forecast artifact.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/08_sfa_forecasting/08_sfa_forecasting.ipynb
```

Runtime scoring stays in `src/telco_digital`. Analysis, training and retained
metrics live only in this folder.
