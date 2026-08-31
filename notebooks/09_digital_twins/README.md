# Capability 09 digital-twin analysis

This executed POC notebook assembles computed customer and retailer twins
from in-memory seed facts. Twins are not persisted.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/09_digital_twins/09_digital_twins.ipynb
```

Runtime services stay in `src/telco_digital`. Analysis and retained metrics
live only in this folder.
