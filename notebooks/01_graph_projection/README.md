# Capability 01 graph projection notebook

This executed notebook reconciles the authoritative PostgreSQL snapshot with
the managed Neo4j projection. It measures node and relationship counts,
projection status, customer degrees, and shared-device evidence.

```powershell
python -m poetry install --extras "dev notebooks"
python -m poetry run jupyter nbconvert --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/01_graph_projection/01_graph_projection.ipynb
```

Credentials are loaded from the gitignored `.env`; they are never written to
notebook outputs.
