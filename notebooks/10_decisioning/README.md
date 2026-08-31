# Capability 10 decisioning analysis

This executed POC notebook compares U001, U002 and U004 next-best actions
from in-memory seed facts. Churn is a constraint, not a discount.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/10_decisioning/10_decisioning.ipynb
```

Runtime services stay in `src/telco_digital`. Analysis and retained metrics
live only in this folder.
