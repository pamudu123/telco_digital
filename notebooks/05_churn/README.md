# Capability 05 churn training

This executed POC notebook trains logistic regression and gradient-boosted
trees on a synthetic labelled population that uses the runtime feature keys.
It retains compact tables, plots and the served coefficient artifact.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/05_churn/05_churn.ipynb
```

Runtime scoring stays in `src/telco_digital`. Analysis, training and retained
metrics live only in this folder.
