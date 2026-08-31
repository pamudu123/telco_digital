# Capability 11 Copilot analysis

This executed POC notebook shows the deterministic fallback for
“Why is U001 receiving this recommendation?”. A live OpenRouter cell is
skipped without `OPENROUTER_API_KEY`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/11_copilot/11_copilot.ipynb
```

Runtime services stay in `src/telco_digital`. Analysis and retained metrics
live only in this folder.
