# Capability 12 FastAPI analysis

This executed POC notebook inspects the thin FastAPI adapter surface:
health, projection lag, model versions, command adapters and query adapters.

```bash
poetry run python notebooks/12_fastapi/generate_outputs.py
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/12_fastapi/12_fastapi.ipynb
```

Runtime adapters stay in `src/telco_digital/api`. Analysis and retained
metrics live only in this folder.
