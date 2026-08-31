"""Score a trained logistic-regression artifact without importing sklearn."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from telco_digital.intelligence.churn.features import (
    CHURN_FEATURE_NAMES,
    MODEL_VERSION,
    ordered_values,
)

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]


def default_artifact_path() -> Path:
    packaged = Path(__file__).resolve().parent / "artifacts" / "churn-model-v1.json"
    if packaged.is_file():
        return packaged
    return (
        Path(__file__).resolve().parents[4]
        / "notebooks"
        / "05_churn"
        / "artifacts"
        / "churn-model-v1.json"
    )


def load_artifact(path: Path | None = None) -> dict[str, Any]:
    artifact_path = path or default_artifact_path()
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Trained churn artifact is missing at {artifact_path}. "
            "Execute notebooks/05_churn/05_churn.ipynb to train and export it."
        )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    names = tuple(payload["feature_names"])
    if names != CHURN_FEATURE_NAMES:
        raise ValueError("Churn artifact feature_names do not match the runtime vector contract.")
    if payload.get("model_type") != "logistic_regression":
        raise ValueError("Runtime scoring only supports the exported logistic regression.")
    return payload


@lru_cache(maxsize=4)
def load_default_artifact() -> dict[str, Any]:
    return load_artifact()


def _sigmoid(logit: float) -> float:
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    exponential = math.exp(logit)
    return exponential / (1.0 + exponential)


def _scale(values: list[float], artifact: dict[str, Any]) -> list[float]:
    means = artifact["scaler_mean"]
    scales = artifact["scaler_scale"]
    scaled: list[float] = []
    for value, mean, scale in zip(values, means, scales, strict=True):
        scaled.append(0.0 if scale == 0 else (value - mean) / scale)
    return scaled


def predict_probability(vector: dict[str, float], artifact: dict[str, Any]) -> float:
    names = tuple(artifact["feature_names"])
    scaled = _scale(ordered_values(vector, names), artifact)
    intercept = float(artifact["intercept"])
    logit = intercept + sum(
        float(coefficient) * value
        for coefficient, value in zip(artifact["coefficients"], scaled, strict=True)
    )
    return round(_sigmoid(logit), 6)


def risk_band(probability: float, artifact: dict[str, Any]) -> RiskBand:
    bands = artifact["risk_bands"]
    if probability >= float(bands["HIGH"]):
        return "HIGH"
    if probability >= float(bands["MEDIUM"]):
        return "MEDIUM"
    return "LOW"


def logit_contributions(vector: dict[str, float], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    names = tuple(artifact["feature_names"])
    scaled = _scale(ordered_values(vector, names), artifact)
    rows: list[dict[str, Any]] = []
    for name, coefficient, scaled_value, raw in zip(
        names, artifact["coefficients"], scaled, ordered_values(vector, names), strict=True
    ):
        contribution = float(coefficient) * scaled_value
        rows.append(
            {
                "feature": name,
                "value": raw,
                "contribution": round(contribution, 6),
                "direction": "increases_risk" if contribution >= 0 else "decreases_risk",
            }
        )
    rows.sort(key=lambda item: (-abs(float(item["contribution"])), item["feature"]))
    return rows


def top_drivers(
    vector: dict[str, float], artifact: dict[str, Any], *, limit: int = 5
) -> list[dict[str, Any]]:
    return logit_contributions(vector, artifact)[:limit]


def artifact_model_version(artifact: dict[str, Any]) -> str:
    return str(artifact.get("model_version") or MODEL_VERSION)
