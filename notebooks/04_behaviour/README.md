# Capability 04 behaviour analysis

This executed POC notebook assigns rule traits for the golden seed customers
and clusters numeric feature vectors against generator personas. It retains
compact tables and plots only.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/04_behaviour/04_behaviour.ipynb
```

Runtime services stay in `src/telco_digital`. Analysis, plots and retained
metrics live only in this folder.
