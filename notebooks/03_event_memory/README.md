# Capability 03 event-memory analysis

This executed POC notebook reconstructs the U001 March Singapore episode from
in-memory seed facts and ranks similar episodes for a later Singapore
situation. It retains compact tables and plots only.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/03_event_memory/03_event_memory.ipynb
```

Runtime services stay in `src/telco_digital`. Analysis, plots and retained
metrics live only in this folder.

The results demonstrate pipeline behavior, not production retrieval quality.
