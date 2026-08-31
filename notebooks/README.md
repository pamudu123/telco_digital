# POC notebooks

Each capability owns one numbered folder. Notebooks contain analysis, training,
evaluation, and plots; runtime services remain under `src/telco_digital`.
Capability 05 trains the served churn artifact in `05_churn`.
Capability 06 ranks catalogue offers in `06_recommendations`.
Capability 07 analyses transaction-only versus graph fraud scores in `07_graph_fraud`.

Install and execute with:

```powershell
python -m poetry install --extras "dev notebooks"
python -m poetry run jupyter nbconvert --execute --inplace notebooks/00_dataset/00_dataset.ipynb
```

Executed notebooks and compact plots/metrics are retained. Credentials, large
raw extracts, caches, and temporary tables must not be committed.
