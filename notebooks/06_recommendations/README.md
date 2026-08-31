# Capability 06 recommendation analysis

This executed POC notebook ranks the seed roaming catalogue for U001's
Singapore situation and checks that inactive or local plans are never offered.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/06_recommendations/06_recommendations.ipynb
```

Runtime services stay in `src/telco_digital`. Analysis and retained metrics
live only in this folder.
