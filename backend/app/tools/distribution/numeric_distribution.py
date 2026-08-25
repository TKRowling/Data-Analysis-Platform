import numpy as np
import pandas as pd

EMPTY = {"counts": [], "edges": [], "mean": None, "median": None, "std": None, "skewness": None, "box": None}


def numeric_distribution(series: pd.Series) -> dict:
    """Histogram, moments, and box quartiles for a numeric column.

    Infinities are dropped alongside nulls: numpy cannot bin a non-finite range, and an
    infinite mean or quartile is not a meaningful statistic to report.
    """
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return dict(EMPTY)
    counts, edges = np.histogram(values, bins="auto")
    return {"counts": counts.tolist(), "edges": edges.tolist(), "mean": float(values.mean()),
            "median": float(values.median()), "std": float(values.std()), "skewness": float(values.skew()),
            "box": {"min": float(values.min()), "q1": float(values.quantile(.25)),
                    "median": float(values.median()), "q3": float(values.quantile(.75)),
                    "max": float(values.max())}}
