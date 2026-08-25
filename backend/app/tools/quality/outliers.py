import numpy as np
import pandas as pd

EMPTY = {"count": 0, "percent": 0.0, "lower_bound": None, "upper_bound": None}


def iqr_outliers(series: pd.Series) -> dict:
    """Flag values beyond 1.5 x IQR from the quartiles. Infinities are excluded, not binned."""
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return dict(EMPTY)
    q1, q3 = values.quantile(.25), values.quantile(.75)
    spread = q3 - q1
    lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
    mask = (values < lower) | (values > upper)
    return {"count": int(mask.sum()), "percent": round(float(mask.mean()) * 100, 2),
            "lower_bound": float(lower), "upper_bound": float(upper)}
