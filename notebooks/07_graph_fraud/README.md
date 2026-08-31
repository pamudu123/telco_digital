# Capability 07 graph fraud analysis

This executed POC notebook scores synthetic golden fixtures with the runtime
rule scorer. It compares transaction-only risk with graph risk and retains
compact tables and plots. No model artifact is served.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/07_graph_fraud/07_graph_fraud.ipynb
```

Runtime scoring stays in `src/telco_digital`. Analysis and retained metrics
live only in this folder.
