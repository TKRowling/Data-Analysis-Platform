import numpy as np
import pandas as pd

MIN_POINTS = 4


def naive_forecast(series: pd.Series, periods: int = 1) -> dict:
    """Repeat the last observed value. Kept as the baseline comparison."""
    values = series.dropna()
    if values.empty:
        raise ValueError("Cannot forecast an empty series")
    return {"method": "last_value", "periods": periods, "forecast": [float(values.iloc[-1])] * periods}


def trend_forecast(series: pd.Series, periods: int = 3) -> dict:
    """Extrapolate a least-squares linear trend forward.

    The index is used for spacing when it is a DatetimeIndex, otherwise positions are assumed
    to be evenly spaced. This is an extrapolation of past behaviour, not a causal model.
    """
    values = series.dropna()
    if len(values) < MIN_POINTS:
        raise ValueError(f"Forecasting needs at least {MIN_POINTS} observations; found {len(values)}")

    if isinstance(values.index, pd.DatetimeIndex):
        positions = values.index.map(pd.Timestamp.toordinal).to_numpy(float)
        step = float(np.median(np.diff(positions))) if len(positions) > 1 else 1.0
        future_positions = positions[-1] + step * np.arange(1, periods + 1)
        labels = [str(pd.Timestamp.fromordinal(int(round(p))).date()) for p in future_positions]
    else:
        positions = np.arange(len(values), dtype=float)
        future_positions = positions[-1] + np.arange(1, periods + 1)
        labels = [str(int(p)) for p in future_positions]

    measurements = values.to_numpy(float)
    slope, intercept = np.polyfit(positions, measurements, 1)
    fitted = slope * positions + intercept
    residual = measurements - fitted
    total = measurements - measurements.mean()
    r2 = float(1 - (residual @ residual) / (total @ total)) if total @ total else 0.0
    projected = slope * future_positions + intercept

    return {
        "method": "linear_trend",
        "periods": periods,
        "observations": int(len(values)),
        "slope": float(slope),
        "intercept": float(intercept),
        "fit_r2": r2,
        "direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat",
        "forecast": [float(v) for v in projected],
        "labels": labels,
    }
