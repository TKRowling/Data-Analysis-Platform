import warnings

import pandas as pd

HIGH_CARDINALITY_RATIO = 0.5
DATE_TOKENS = ("date", "time", "created", "updated", "timestamp")


def datatype_summary(frame: pd.DataFrame) -> list[dict]:
    return [{"column": c, "dtype": str(frame[c].dtype), "python_types": sorted({type(v).__name__ for v in frame[c].dropna().head(100)})} for c in frame]


def _numeric_like(values: pd.Series) -> float:
    """Share of non-null text values that would parse cleanly as numbers."""
    converted = pd.to_numeric(values, errors="coerce")
    return float(converted.notna().mean()) if len(values) else 0.0


def _date_like(values: pd.Series) -> float:
    if not len(values):
        return 0.0
    with warnings.catch_warnings():
        # A heuristic probe: mixed or unparseable formats are the answer, not a problem.
        warnings.simplefilter("ignore", UserWarning)
        converted = pd.to_datetime(values, errors="coerce")
    return float(converted.notna().mean())


def datatype_issues(frame: pd.DataFrame) -> list[dict]:
    """Flag columns whose stored dtype disagrees with the values they hold."""
    issues: list[dict] = []
    rows = max(len(frame), 1)
    for name in frame.columns:
        series = frame[name]
        values = series.dropna()
        if values.empty:
            issues.append({"column": name, "dtype": str(series.dtype), "issue": "empty_column",
                           "detail": "Every value is missing.", "severity": "high"})
            continue
        if pd.api.types.is_object_dtype(series):
            sample = values.head(500)
            types = sorted({type(v).__name__ for v in sample})
            if len(types) > 1:
                issues.append({"column": name, "dtype": str(series.dtype), "issue": "mixed_types",
                               "detail": f"Holds multiple Python types: {', '.join(types)}.", "severity": "high"})
            elif _numeric_like(sample) >= 0.9:
                issues.append({"column": name, "dtype": str(series.dtype), "issue": "numeric_stored_as_text",
                               "detail": "At least 90% of values parse as numbers but the column is text.", "severity": "high"})
            elif _date_like(sample) >= 0.9 or any(token in name.lower() for token in DATE_TOKENS) and _date_like(sample) >= 0.7:
                issues.append({"column": name, "dtype": str(series.dtype), "issue": "date_stored_as_text",
                               "detail": "Values parse as dates but the column is text.", "severity": "medium"})
        unique = int(series.nunique(dropna=True))
        if not pd.api.types.is_numeric_dtype(series) and unique / rows >= HIGH_CARDINALITY_RATIO and unique > 20:
            issues.append({"column": name, "dtype": str(series.dtype), "issue": "high_cardinality",
                           "detail": f"{unique} distinct values across {rows} rows — likely an identifier, not a category.", "severity": "low"})
        if pd.api.types.is_numeric_dtype(series) and unique <= 2 and not pd.api.types.is_bool_dtype(series):
            issues.append({"column": name, "dtype": str(series.dtype), "issue": "numeric_flag",
                           "detail": "Only two distinct numeric values — consider treating this as a boolean flag.", "severity": "low"})
    return issues
