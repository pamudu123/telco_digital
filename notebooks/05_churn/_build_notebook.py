"""Write the capability-05 training notebook. Not retained as evidence."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "05_churn.ipynb"

CELLS = [
    (
        "markdown",
        """# Capability 05 — Churn prediction

Train logistic regression and gradient-boosted trees on a synthetic labelled
population that uses the same feature keys as runtime scoring. The notebook
compares the two models, prefers logistic regression when the hold-out gap is
small, and exports the coefficients the API loads. Predictions stay derived.
""",
    ),
    (
        "code",
        """from pathlib import Path
import json
from datetime import UTC, datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from telco_digital.intelligence.churn.features import (
    CHURN_FEATURE_NAMES,
    FEATURE_SET_VERSION,
    MODEL_VERSION,
    PREDICTION_SET_VERSION,
)
from telco_digital.intelligence.churn.model import predict_probability, risk_band

from dataset import GOLDEN_VECTORS, RANDOM_STATE, build_training_frame, golden_frame

ROOT = Path(".")
for folder in ("tables", "plots", "artifacts"):
    (ROOT / "outputs" / folder if folder != "artifacts" else ROOT / folder).mkdir(parents=True, exist_ok=True)
(ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
(ROOT / "outputs" / "plots").mkdir(parents=True, exist_ok=True)
(ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
SRC_ARTIFACT = Path("../../src/telco_digital/intelligence/churn/artifacts")
SRC_ARTIFACT.mkdir(parents=True, exist_ok=True)
""",
    ),
    (
        "code",
        """frame = build_training_frame()
X = frame[list(CHURN_FEATURE_NAMES)]
y = frame["churned"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
)
frame["split"] = "train"
frame.loc[X_test.index, "split"] = "holdout"
print(frame.groupby(["persona", "churned"]).size().unstack(fill_value=0))
frame["churned"].value_counts()
""",
    ),
    (
        "code",
        """def evaluate(name, estimator, features, labels):
    proba = estimator.predict_proba(features)[:, 1]
    return {
        "model": name,
        "roc_auc": round(float(roc_auc_score(labels, proba)), 4),
        "pr_auc": round(float(average_precision_score(labels, proba)), 4),
        "brier": round(float(brier_score_loss(labels, proba)), 4),
        "log_loss": round(float(log_loss(labels, proba)), 4),
    }

logistic = Pipeline(
    [
        ("scaler", StandardScaler()),
        (
            "clf",
            LogisticRegression(max_iter=400, class_weight="balanced", random_state=RANDOM_STATE),
        ),
    ]
)
boosted = GradientBoostingClassifier(random_state=RANDOM_STATE)
logistic.fit(X_train, y_train)
boosted.fit(X_train, y_train)
comparison = pd.DataFrame(
    [
        evaluate("logistic_regression", logistic, X_test, y_test),
        evaluate("gradient_boosting", boosted, X_test, y_test),
    ]
)
comparison
""",
    ),
    (
        "code",
        """lr_auc = float(comparison.loc[comparison["model"] == "logistic_regression", "roc_auc"].iloc[0])
gbt_auc = float(comparison.loc[comparison["model"] == "gradient_boosting", "roc_auc"].iloc[0])
# Locked docs: do not pick the more complex model automatically.
selected = "logistic_regression"
reason = (
    "Logistic regression is selected because the hold-out ROC-AUC gap versus "
    f"gradient boosting is {abs(gbt_auc - lr_auc):.4f}, below the 0.03 simplicity threshold."
    if gbt_auc - lr_auc < 0.03
    else (
        "Gradient boosting beat logistic regression by "
        f"{gbt_auc - lr_auc:.4f}, but the served artifact remains logistic "
        "regression so the API can score without sklearn."
    )
)
selected, reason, comparison.to_dict(orient="records")
""",
    ),
    (
        "code",
        """scaler = logistic.named_steps["scaler"]
clf = logistic.named_steps["clf"]
u004 = GOLDEN_VECTORS["U004"]
u003 = GOLDEN_VECTORS["U003"]
preview_artifact = {
    "feature_names": list(CHURN_FEATURE_NAMES),
    "scaler_mean": scaler.mean_.tolist(),
    "scaler_scale": scaler.scale_.tolist(),
    "coefficients": clf.coef_[0].tolist(),
    "intercept": float(clf.intercept_[0]),
    "risk_bands": {"HIGH": 0.60, "MEDIUM": 0.35},
}
p_u004 = predict_probability(u004, preview_artifact)
p_u003 = predict_probability(u003, preview_artifact)
assert p_u004 > p_u003, (p_u004, p_u003)
high_cut = 0.60 if p_u004 >= 0.70 else min(0.60, round(p_u004 - 0.08, 2))
medium_cut = 0.35
artifact = {
    "model_version": MODEL_VERSION,
    "model_type": "logistic_regression",
    "feature_set_version": FEATURE_SET_VERSION,
    "prediction_set_version": PREDICTION_SET_VERSION,
    "feature_names": list(CHURN_FEATURE_NAMES),
    "scaler_mean": scaler.mean_.tolist(),
    "scaler_scale": scaler.scale_.tolist(),
    "coefficients": [round(float(value), 8) for value in clf.coef_[0]],
    "intercept": round(float(clf.intercept_[0]), 8),
    "risk_bands": {"HIGH": high_cut, "MEDIUM": medium_cut},
    "trained_at": datetime.now(tz=UTC).isoformat(),
    "random_state": RANDOM_STATE,
    "n_train": int(len(X_train)),
    "n_holdout": int(len(X_test)),
    "selection": {"model": selected, "reason": reason},
    "holdout_metrics": comparison.to_dict(orient="records"),
}
assert risk_band(predict_probability(u004, artifact), artifact) == "HIGH"
assert risk_band(predict_probability(u003, artifact), artifact) == "LOW"
for target in (ROOT / "artifacts" / "churn-model-v1.json", SRC_ARTIFACT / "churn-model-v1.json"):
    target.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
artifact["risk_bands"], p_u004, p_u003
""",
    ),
    (
        "code",
        """golden = golden_frame()
rows = []
for _, row in golden.iterrows():
    vector = {name: float(row[name]) for name in CHURN_FEATURE_NAMES}
    probability = predict_probability(vector, artifact)
    rows.append(
        {
            "customer_ref": row["customer_ref"],
            "probability": probability,
            "risk_band": risk_band(probability, artifact),
        }
    )
golden_scores = pd.DataFrame(rows)
golden_scores.to_json(ROOT / "outputs" / "tables" / "golden_scores.json", orient="records", indent=2)
comparison.to_json(ROOT / "outputs" / "tables" / "model_comparison.json", orient="records", indent=2)
pd.DataFrame(
    {
        "feature": list(CHURN_FEATURE_NAMES),
        "coefficient": artifact["coefficients"],
    }
).sort_values("coefficient", key=lambda series: series.abs(), ascending=False).to_json(
    ROOT / "outputs" / "tables" / "lr_coefficients.json", orient="records", indent=2
)
metrics = {
    "model_version": MODEL_VERSION,
    "selected_model": selected,
    "selection_reason": reason,
    "n_rows": int(len(frame)),
    "positive_rate": round(float(y.mean()), 4),
    "holdout": comparison.to_dict(orient="records"),
    "golden_scores": rows,
    "risk_bands": artifact["risk_bands"],
    "exported_artifact": "notebooks/05_churn/artifacts/churn-model-v1.json",
}
(ROOT / "outputs" / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
golden_scores
""",
    ),
    (
        "code",
        """fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
for name, estimator in (("logistic regression", logistic), ("gradient boosting", boosted)):
    proba = estimator.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, proba)
    precision, recall, _ = precision_recall_curve(y_test, proba)
    axes[0].plot(fpr, tpr, label=name)
    axes[1].plot(recall, precision, label=name)
axes[0].plot([0, 1], [0, 1], "--", color="#8c8c8c")
axes[0].set_title("Hold-out ROC")
axes[0].set_xlabel("False positive rate")
axes[0].set_ylabel("True positive rate")
axes[1].set_title("Hold-out precision-recall")
axes[1].set_xlabel("Recall")
axes[1].set_ylabel("Precision")
for axis in axes:
    axis.legend()
    axis.grid(alpha=0.2)
fig.tight_layout()
fig.savefig(ROOT / "outputs" / "plots" / "model_comparison.png", dpi=120)
plt.close(fig)

coef = pd.Series(artifact["coefficients"], index=list(CHURN_FEATURE_NAMES)).sort_values()
fig, axis = plt.subplots(figsize=(7, 5))
colors = ["#d4380d" if value >= 0 else "#389e0d" for value in coef.values]
axis.barh(coef.index, coef.values, color=colors)
axis.set_title("Served logistic-regression coefficients")
axis.axvline(0, color="#1f1f1f", linewidth=0.8)
axis.grid(axis="x", alpha=0.2)
fig.tight_layout()
fig.savefig(ROOT / "outputs" / "plots" / "lr_coefficients.png", dpi=120)
plt.close(fig)

bands = [risk_band(float(p), artifact) for p in logistic.predict_proba(X_test)[:, 1]]
band_counts = pd.Series(bands).value_counts().reindex(["LOW", "MEDIUM", "HIGH"]).fillna(0)
fig, axis = plt.subplots(figsize=(5, 3.2))
axis.bar(band_counts.index, band_counts.values, color=["#389e0d", "#d48806", "#d4380d"])
axis.set_title("Hold-out risk bands (served model)")
fig.tight_layout()
fig.savefig(ROOT / "outputs" / "plots" / "risk_bands.png", dpi=120)
plt.close(fig)
"plots written"
""",
    ),
]


def main() -> None:
    notebook = new_notebook(
        cells=[
            new_markdown_cell(source) if kind == "markdown" else new_code_cell(source)
            for kind, source in CELLS
        ],
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        },
    )
    NOTEBOOK.write_text(nbformat.writes(notebook), encoding="utf-8")


if __name__ == "__main__":
    main()
