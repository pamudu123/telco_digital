# POC notebooks

Each capability owns one numbered folder. Notebooks contain analysis, training,
evaluation, and plots; runtime services remain under `src/telco_digital`.
Capability 05 trains the served churn artifact in `05_churn`.
Capability 06 ranks catalogue offers in `06_recommendations`.
Capability 07 analyses transaction-only versus graph fraud scores in `07_graph_fraud`.
Capability 08 trains the served SFA forecast artifact in `08_sfa_forecasting`.
Capability 09 assembles computed twins in `09_digital_twins`.
Capability 10 evaluates next-best actions in `10_decisioning`.
Capability 11 demonstrates Copilot fallback in `11_copilot`.

Install and execute with:

```powershell
python -m poetry install --extras "dev notebooks"
python -m poetry run jupyter nbconvert --execute --inplace notebooks/00_dataset/00_dataset.ipynb
```

Executed notebooks and compact plots/metrics are retained. Credentials, large
raw extracts, caches, and temporary tables must not be committed.
