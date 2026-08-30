# Capability 00 — dataset analysis

`00_dataset.ipynb` reads the validation report produced by
`scripts/generate_poc_dataset.py`, summarizes the generated cross-domain POC
dataset, and writes plots under `outputs/plots/`.

The notebook is analytical and read-only. Loading and reset operations stay in
the explicit CLI script.
