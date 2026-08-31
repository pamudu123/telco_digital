"""Train naive, moving-average, ARIMA and Prophet models for capability 08.

Runtime scoring does not import these libraries. This module writes the JSON
artifact the API loads and the compact notebook evidence files.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dataset import HOLDOUT_END, TRAIN_END, hero_frame, split_hero

from telco_digital.intelligence.forecasting.models import forecast_from_history
from telco_digital.intelligence.forecasting.series import (
    FORECAST_SET_VERSION,
    HERO_PRODUCT_CODE,
    HERO_RETAILER_REF,
    MODEL_VERSION,
    SERIES_START,
)

HOLDOUT_HORIZON = 28
DEMO_HORIZON = 7


def _metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    pairs = [(float(y), float(yhat)) for y, yhat in zip(actual, predicted, strict=True)]
    errors = [yhat - y for y, yhat in pairs]
    abs_errors = [abs(item) for item in errors]
    sq_errors = [item * item for item in errors]
    mape = [abs(err) / y for (y, _yhat), err in zip(pairs, abs_errors, strict=True) if y > 1e-6]
    return {
        "mae": round(float(np.mean(abs_errors)), 4),
        "rmse": round(float(math.sqrt(float(np.mean(sq_errors)))), 4),
        "mape": round(float(np.mean(mape) * 100.0), 4) if mape else 0.0,
    }


def _baseline_forecasts(train_y: list[float], horizon: int) -> dict[str, list[float]]:
    from telco_digital.intelligence.forecasting.models import (
        moving_average_forecast,
        naive_forecast,
        seasonal_naive_forecast,
    )

    return {
        "naive": naive_forecast(train_y, horizon),
        "seasonal_naive": seasonal_naive_forecast(train_y, horizon),
        "moving_average": moving_average_forecast(train_y, horizon),
    }


def _fit_arima(train: pd.DataFrame, horizon: int) -> tuple[list[float], dict[str, Any]]:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    y = train["y"].to_numpy(dtype=float)
    candidates: list[tuple[str, Any, tuple[int, int, int], tuple[int, int, int, int]]] = []
    for order in ((1, 1, 1), (2, 1, 1), (1, 1, 2)):
        try:
            fitted = ARIMA(y, order=order).fit()
            candidates.append((str(fitted.aic), fitted, order, (0, 0, 0, 0)))
        except Exception:
            continue
    try:
        seasonal = SARIMAX(y, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7), enforce_stationarity=False)
        fitted = seasonal.fit(disp=False)
        candidates.append((str(fitted.aic), fitted, (1, 1, 1), (1, 1, 1, 7)))
    except Exception:
        pass
    if not candidates:
        raise RuntimeError("ARIMA fitting failed for every candidate order.")
    _aic, best, order, seasonal_order = min(candidates, key=lambda item: float(item[0]))
    forecast = [max(0.0, float(value)) for value in best.forecast(horizon)]
    named = {
        str(name): float(value)
        for name, value in zip(best.param_names, np.asarray(best.params, dtype=float), strict=False)
    }
    ar_params = [value for name, value in named.items() if name.startswith("ar.")]
    ma_params = [value for name, value in named.items() if name.startswith("ma.")]
    intercept = float(named.get("const", named.get("intercept", 0.0)))
    residuals = [float(value) for value in np.asarray(best.resid, dtype=float)[-12:]]
    spec = {
        "order": list(order),
        "seasonal_order": list(seasonal_order),
        "seasonal_period": seasonal_order[3],
        "seasonal_d": seasonal_order[1],
        "ar": ar_params,
        "ma": ma_params,
        "intercept": intercept,
        "residuals": residuals,
        "aic": round(float(best.aic), 4),
    }
    return forecast, spec


def _fit_prophet(train: pd.DataFrame, horizon: int) -> tuple[list[float], dict[str, Any]]:
    from prophet import Prophet

    frame = pd.DataFrame(
        {"ds": pd.to_datetime(train["ds"]).dt.tz_localize(None), "y": train["y"].astype(float)}
    )
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=0.12,
    )
    model.fit(frame)
    future = model.make_future_dataframe(periods=horizon, freq="D")
    predicted = model.predict(future).tail(horizon)["yhat"].tolist()
    t_scale = model.t_scale
    t_scale_days = float(getattr(t_scale, "days", t_scale))
    spec = {
        "start": SERIES_START.isoformat(),
        "t_scale_days": t_scale_days,
        "y_scale": float(model.y_scale),
        "k": float(np.asarray(model.params["k"]).reshape(-1)[0]),
        "m": float(np.asarray(model.params["m"]).reshape(-1)[0]),
        "deltas": [float(value) for value in np.asarray(model.params["delta"]).reshape(-1)],
        "changepoints_t": [float(value) for value in np.asarray(model.changepoints_t).reshape(-1)],
        "beta": [float(value) for value in np.asarray(model.params["beta"]).reshape(-1)],
        "weekly_order": 3,
        "yearly_order": 0,
        "history_length": int(len(train)),
        "train_mean": round(float(train["y"].tail(28).mean()), 6),
    }
    return [max(0.0, float(value)) for value in predicted], spec


def _fourier_fallback(train: pd.DataFrame, horizon: int) -> tuple[list[float], dict[str, Any]]:
    """Additive weekly + yearly Fourier trend if Prophet cannot be imported."""
    y = train["y"].to_numpy(dtype=float)
    days = np.arange(len(y), dtype=float)
    columns = [np.ones(len(y)), days / max(len(y) - 1, 1)]
    for order, period in ((3, 7.0), (10, 365.25)):
        for harmonic in range(1, order + 1):
            columns.append(np.sin(2 * np.pi * harmonic * days / period))
            columns.append(np.cos(2 * np.pi * harmonic * days / period))
    design = np.column_stack(columns)
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    future_days = np.arange(len(y), len(y) + horizon, dtype=float)
    future_cols = [np.ones(horizon), future_days / max(len(y) - 1, 1)]
    for order, period in ((3, 7.0), (10, 365.25)):
        for harmonic in range(1, order + 1):
            future_cols.append(np.sin(2 * np.pi * harmonic * future_days / period))
            future_cols.append(np.cos(2 * np.pi * harmonic * future_days / period))
    predicted = np.column_stack(future_cols) @ coef
    spec = {
        "start": SERIES_START.isoformat(),
        "t_scale_days": float(max(len(y) - 1, 1)),
        "y_scale": 1.0,
        "k": float(coef[1]),
        "m": float(coef[0]),
        "deltas": [],
        "changepoints_t": [],
        "beta": [float(value) for value in coef[2:]],
        "weekly_order": 3,
        "yearly_order": 10,
        "history_length": int(len(train)),
        "train_mean": round(float(train["y"].tail(28).mean()), 6),
        "fallback": True,
    }
    return [max(0.0, float(value)) for value in predicted], spec


def run_training(root: Path | None = None) -> dict[str, Any]:
    root = Path(root or ".")
    tables = root / "outputs" / "tables"
    plots = root / "outputs" / "plots"
    artifacts = root / "artifacts"
    for folder in (tables, plots, artifacts):
        folder.mkdir(parents=True, exist_ok=True)

    train, holdout = split_hero()
    actual = holdout["y"].astype(float).tolist()
    train_y = train["y"].astype(float).tolist()
    comparison: dict[str, dict[str, float]] = {}
    forecasts: dict[str, list[float]] = _baseline_forecasts(train_y, len(actual))
    for name, predicted in forecasts.items():
        comparison[name] = _metrics(actual, predicted)

    arima_forecast, arima_spec = _fit_arima(train, len(actual))
    forecasts["arima"] = arima_forecast
    comparison["arima"] = _metrics(actual, arima_forecast)

    prophet_backend = "prophet"
    try:
        prophet_forecast, prophet_spec = _fit_prophet(train, len(actual))
    except Exception:
        prophet_backend = "fourier_fallback"
        prophet_forecast, prophet_spec = _fourier_fallback(train, len(actual))
    forecasts["prophet"] = prophet_forecast
    comparison["prophet"] = _metrics(actual, prophet_forecast)

    ranked = sorted(comparison.items(), key=lambda item: (item[1]["mape"], item[1]["mae"]))
    served = "prophet" if comparison["prophet"]["mape"] <= comparison["arima"]["mape"] + 1.5 else "arima"
    if ranked[0][0] in {"prophet", "arima"}:
        served = ranked[0][0]

    payload = {
        "model_version": MODEL_VERSION,
        "forecast_set_version": FORECAST_SET_VERSION,
        "served_model": served,
        "model_type": served,
        "prophet_backend": prophet_backend,
        "hero": {"retailer_ref": HERO_RETAILER_REF, "product_code": HERO_PRODUCT_CODE},
        "train_end": TRAIN_END.date().isoformat(),
        "holdout_end": HOLDOUT_END.date().isoformat(),
        "comparison": comparison,
        "served_holdout": comparison[served],
        "arima": arima_spec,
        "prophet": prophet_spec,
        "n_train": int(len(train)),
        "n_holdout": int(len(holdout)),
    }

    artifact_path = artifacts / "sfa-forecast-v1.json"
    artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    src_dir = root.resolve().parents[1] / "src" / "telco_digital" / "intelligence" / "forecasting" / "artifacts"
    src_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact_path, src_dir / "sfa-forecast-v1.json")

    reconstructed = forecast_from_history(train_y, len(actual), payload, model=served)
    reconstruction = _metrics(actual, reconstructed)

    hero = hero_frame()
    demo_history = hero[hero["ds"] <= HOLDOUT_END]
    demo_future = hero[hero["ds"] > HOLDOUT_END].head(DEMO_HORIZON)
    demo_forecast = forecast_from_history(
        demo_history["y"].astype(float).tolist(), DEMO_HORIZON, payload
    )
    demo_actual = demo_future["y"].astype(float).tolist()
    demo_on_hand = float(demo_history.iloc[-1]["on_hand"])

    metrics = {
        "model_version": MODEL_VERSION,
        "served_model": served,
        "prophet_backend": prophet_backend,
        "comparison": comparison,
        "reconstruction": reconstruction,
        "hero": {
            "retailer_ref": HERO_RETAILER_REF,
            "product_code": HERO_PRODUCT_CODE,
            "as_of": HOLDOUT_END.date().isoformat(),
            "on_hand": round(demo_on_hand, 2),
            "forecast_7d": round(float(sum(demo_forecast)), 2),
            "actual_7d": round(float(sum(demo_actual)), 2) if demo_actual else None,
            "stockout_warning": demo_on_hand < sum(demo_forecast),
        },
    }
    (root / "outputs" / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    tables.joinpath("model_comparison.json").write_text(
        json.dumps(
            [{"model": name, **values} for name, values in comparison.items()],
            indent=2,
        ),
        encoding="utf-8",
    )
    tables.joinpath("hero_forecast.json").write_text(
        json.dumps(metrics["hero"], indent=2),
        encoding="utf-8",
    )
    tables.joinpath("reconstruction.json").write_text(json.dumps(reconstruction, indent=2), encoding="utf-8")
    return {
        "payload": payload,
        "metrics": metrics,
        "train": train,
        "holdout": holdout,
        "forecasts": forecasts,
        "demo_history": demo_history,
        "demo_forecast": demo_forecast,
        "demo_actual": demo_actual,
    }


if __name__ == "__main__":
    run_training(Path(__file__).resolve().parent)
