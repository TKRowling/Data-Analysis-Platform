"""Shared dataframe sanitizers. Everything crossing the HTTP boundary goes through here."""
import numpy as np
import pandas as pd


def json_records(frame: pd.DataFrame) -> list[dict]:
    """Rows as JSON-safe dicts: NaN and +/-inf become None."""
    safe = frame.replace([np.inf, -np.inf], np.nan)
    return safe.astype(object).where(pd.notnull(safe), None).to_dict(orient="records")


def json_safe_records(frame: pd.DataFrame) -> list[dict]:
    """Backwards-compatible alias for :func:`json_records`."""
    return json_records(frame)


def finite(value):
    """Scalar sanitizer: NaN, inf, and None all collapse to None."""
    if value is None:
        return None
    try:
        if pd.isna(value) or np.isinf(value):
            return None
    except (TypeError, ValueError):
        return None
    return round(float(value), 6)


def finite_series(series: pd.Series) -> pd.Series:
    """Numeric values only, with nulls and infinities removed."""
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()


def column_kind(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series): return "datetime"
    if pd.api.types.is_bool_dtype(series): return "boolean"
    if pd.api.types.is_numeric_dtype(series): return "numeric"
    return "categorical"


def numeric_columns(frame: pd.DataFrame) -> list[str]:
    return list(frame.select_dtypes(include=np.number).columns)


def categorical_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c not in numeric_columns(frame)]
