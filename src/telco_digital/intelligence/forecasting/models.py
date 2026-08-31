"""Score notebook-trained forecast artifacts without importing Prophet or statsmodels."""

from __future__ import annotations

import json
import math
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from telco_digital.intelligence.forecasting.series import MODEL_VERSION, SERIES_START


def default_artifact_path() -> Path:
    packaged = Path(__file__).resolve().parent / "artifacts" / "sfa-forecast-v1.json"
    if packaged.is_file():
        return packaged
    return (
        Path(__file__).resolve().parents[4]
        / "notebooks"
        / "08_sfa_forecasting"
        / "artifacts"
        / "sfa-forecast-v1.json"
    )


def load_artifact(path: Path | None = None) -> dict[str, Any]:
    artifact_path = path or default_artifact_path()
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Trained forecast artifact is missing at {artifact_path}. "
            "Execute notebooks/08_sfa_forecasting/08_sfa_forecasting.ipynb to train and export it."
        )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if payload.get("model_version") != MODEL_VERSION:
        raise ValueError("Forecast artifact model_version does not match the runtime contract.")
    return payload


@lru_cache(maxsize=4)
def load_default_artifact() -> dict[str, Any]:
    return load_artifact()


def artifact_model_version(artifact: dict[str, Any]) -> str:
    return str(artifact.get("model_version") or MODEL_VERSION)


def naive_forecast(history: list[float], horizon: int) -> list[float]:
    if not history:
        return [0.0] * horizon
    return [round(history[-1], 4) for _ in range(horizon)]


def seasonal_naive_forecast(history: list[float], horizon: int, period: int = 7) -> list[float]:
    if not history:
        return [0.0] * horizon
    values = history[-period:] if len(history) >= period else history
    return [round(values[index % len(values)], 4) for index in range(horizon)]


def moving_average_forecast(history: list[float], horizon: int, window: int = 7) -> list[float]:
    if not history:
        return [0.0] * horizon
    sample = history[-window:]
    mean = sum(sample) / len(sample)
    return [round(mean, 4) for _ in range(horizon)]


def _difference(values: list[float], order: int) -> list[float]:
    differenced = list(values)
    for _ in range(order):
        differenced = [b - a for a, b in zip(differenced, differenced[1:], strict=False)]
    return differenced


def _undifference(last_levels: list[float], diffs: list[float], order: int) -> list[float]:
    levels = list(last_levels)
    forecasts = []
    for diff in diffs:
        if order == 0:
            value = diff
        elif order == 1:
            value = levels[-1] + diff
        else:
            value = 2 * levels[-1] - levels[-2] + diff
        forecasts.append(value)
        levels.append(value)
        if len(levels) > order:
            levels = levels[-max(order, 1) :]
    return forecasts


def arima_forecast(history: list[float], horizon: int, artifact: dict[str, Any]) -> list[float]:
    """Apply exported ARIMA coefficients with future innovations set to zero."""
    spec = artifact["arima"]
    order = tuple(spec["order"])
    p, d, q = (int(order[0]), int(order[1]), int(order[2]))
    ar = [float(value) for value in spec.get("ar", [])]
    ma = [float(value) for value in spec.get("ma", [])]
    intercept = float(spec.get("intercept", 0.0))
    if len(history) < max(p + d + 2, 8):
        return moving_average_forecast(history, horizon)
    work = list(history)
    seasonal_period = int(spec.get("seasonal_period") or 0)
    seasonal_d = int(spec.get("seasonal_d") or 0)
    seasonal_history: list[float] = []
    if seasonal_period and seasonal_d:
        seasonal_history = work[:]
        work = [
            work[index] - work[index - seasonal_period]
            for index in range(seasonal_period, len(work))
        ]
    differenced = _difference(work, d)
    residuals = [float(value) for value in spec.get("residuals", [])][-max(q, 1) :]
    while len(residuals) < q:
        residuals.insert(0, 0.0)
    window = differenced[-max(p, 1) :] if p else []
    future_diffs: list[float] = []
    for _ in range(horizon):
        recent_ar = reversed(window[-p:] if p else [])
        recent_ma = reversed(residuals[-q:] if q else [])
        ar_term = sum(coeff * value for coeff, value in zip(ar, recent_ar, strict=False))
        ma_term = sum(coeff * value for coeff, value in zip(ma, recent_ma, strict=False))
        prediction = intercept + ar_term + ma_term
        future_diffs.append(prediction)
        if p:
            window.append(prediction)
        residuals.append(0.0)
    last_levels = work[-max(d, 1) :]
    restored = _undifference(last_levels, future_diffs, d)
    if seasonal_period and seasonal_d:
        restored = [
            seasonal_history[-seasonal_period + index] + value
            if len(seasonal_history) >= seasonal_period
            else value
            for index, value in enumerate(restored)
        ]
    return [round(max(0.0, value), 4) for value in restored]


def _fourier_row(day_index: float, period: float, order: int) -> list[float]:
    columns: list[float] = []
    for harmonic in range(1, order + 1):
        angle = 2.0 * math.pi * harmonic * day_index / period
        columns.append(math.sin(angle))
        columns.append(math.cos(angle))
    return columns


def _days_since_epoch(day: date) -> float:
    return float((day - date(1970, 1, 1)).days)


def prophet_forecast(history: list[float], horizon: int, artifact: dict[str, Any]) -> list[float]:
    """Reconstruct Prophet's additive forecast from exported trend and Fourier terms."""
    spec = artifact["prophet"]
    if len(history) < 14:
        return seasonal_naive_forecast(history, horizon)
    start = date.fromisoformat(str(spec.get("start") or SERIES_START.isoformat()))
    weekly_order = int(spec["weekly_order"])
    yearly_order = int(spec["yearly_order"])
    beta = [float(value) for value in spec["beta"]]
    k = float(spec["k"])
    intercept = float(spec["m"])
    deltas = [float(value) for value in spec.get("deltas", [])]
    changepoints = [float(value) for value in spec.get("changepoints_t", [])]
    t_scale = float(spec.get("t_scale_days") or spec.get("t_scale") or 1.0)
    y_scale = float(spec["y_scale"])
    local_mean = sum(history[-28:]) / min(len(history), 28)
    trained_mean = float(spec.get("train_mean", local_mean))
    scale = local_mean / trained_mean if trained_mean else 1.0

    forecasts: list[float] = []
    for step in range(1, horizon + 1):
        day = start + timedelta(days=len(history) - 1 + step)
        t = (day - start).days / t_scale
        trend = k * t + intercept
        for delta, point in zip(deltas, changepoints, strict=False):
            if t >= point:
                trend += delta * (t - point)
        fourier = _fourier_row(_days_since_epoch(day), 7.0, weekly_order) + _fourier_row(
            _days_since_epoch(day), 365.25, yearly_order
        )
        seasonal = sum(coeff * value for coeff, value in zip(beta, fourier, strict=False))
        yhat = (trend + seasonal) * y_scale * scale
        forecasts.append(round(max(0.0, yhat), 4))
    return forecasts


def forecast_from_history(
    history: list[float],
    horizon: int,
    artifact: dict[str, Any],
    *,
    model: str | None = None,
) -> list[float]:
    chosen = model or str(artifact.get("served_model") or "prophet")
    if chosen == "naive":
        return naive_forecast(history, horizon)
    if chosen == "seasonal_naive":
        return seasonal_naive_forecast(history, horizon)
    if chosen == "moving_average":
        return moving_average_forecast(history, horizon)
    if chosen == "arima":
        return arima_forecast(history, horizon, artifact)
    if chosen == "prophet":
        return prophet_forecast(history, horizon, artifact)
    raise ValueError(f"Unsupported served forecast model: {chosen}")
