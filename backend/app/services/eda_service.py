"""Exploratory data analysis use cases.

Every figure here is produced by a deterministic function in ``app.tools``.
This module only assembles those results into API response shapes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.exceptions import AnalysisError
from app.tools.correlation import correlation_matrix
from app.tools.distribution import categorical_distribution, numeric_distribution
from app.tools.quality import datatype_issues, duplicate_summary, iqr_outliers, missing_summary
from app.utils.dataframe_utils import column_kind, finite, finite_series, json_records

from app.tools.correlation.thresholds import STRONG as STRONG_CORRELATION

__all__ = ["overview", "statistics", "quality", "correlation", "distribution", "column_kind", "finite"]


def overview(record) -> dict:
    frame = record.frame
    columns = []
    kinds = {"numeric": 0, "categorical": 0, "datetime": 0, "boolean": 0}
    for name in frame.columns:
        series = frame[name]
        kind = column_kind(series); kinds[kind] += 1
        sample = series.dropna().iloc[0] if series.notna().any() else None
        columns.append({"name": name, "type": str(series.dtype), "kind": kind,
                        "non_null": int(series.notna().sum()), "missing": int(series.isna().sum()),
                        "unique": int(series.nunique(dropna=True)), "sample": str(sample) if sample is not None else None})
    return {"rows": len(frame), "columns_count": len(frame.columns),
            "memory_bytes": int(frame.memory_usage(deep=True).sum()), "kinds": kinds, "columns": columns,
            "sample": json_records(frame.head(8))}


def statistics(record) -> dict:
    frame = record.frame
    numeric = []
    for name in frame.select_dtypes(include=np.number).columns:
        s = finite_series(frame[name])
        numeric.append({"column": name, "count": int(s.count()), "mean": finite(s.mean()),
                        "median": finite(s.median()), "std": finite(s.std()), "min": finite(s.min()),
                        "q25": finite(s.quantile(.25)), "q75": finite(s.quantile(.75)),
                        "max": finite(s.max()), "skewness": finite(s.skew()), "kurtosis": finite(s.kurt())})
    categorical = []
    for name in frame.select_dtypes(exclude=np.number).columns:
        counts = frame[name].fillna("(missing)").astype(str).value_counts().head(10)
        categorical.append({"column": name, "unique": int(frame[name].nunique(dropna=True)),
                            "missing": int(frame[name].isna().sum()),
                            "top_values": [{"value": k, "count": int(v), "proportion": round(v / max(len(frame), 1), 4)} for k, v in counts.items()]})
    histograms = []
    for name in frame.select_dtypes(include=np.number).columns:
        shape = numeric_distribution(frame[name])
        histograms.append({"column": name, "counts": shape["counts"], "edges": [finite(v) for v in shape["edges"]]})
    return {"numeric": numeric, "categorical": categorical, "histograms": histograms}


def quality(record) -> dict:
    frame = record.frame
    rows = max(len(frame), 1)
    missing = missing_summary(frame)
    duplicates = duplicate_summary(frame)
    outliers = []
    for name in frame.select_dtypes(include=np.number).columns:
        series = frame[name].dropna()
        if series.empty:
            outliers.append({"column": name, "count": 0, "percent": 0.0, "lower_bound": None, "upper_bound": None})
            continue
        summary = iqr_outliers(frame[name])
        outliers.append({"column": name, "count": summary["count"], "percent": summary["percent"],
                         "lower_bound": finite(summary["lower_bound"]), "upper_bound": finite(summary["upper_bound"])})
    numeric_cells = max(frame.select_dtypes(include=np.number).size, 1)
    completeness = 1 - frame.isna().sum().sum() / max(frame.size, 1)
    uniqueness = 1 - duplicates["count"] / rows
    outlier_rate = sum(x["count"] for x in outliers) / numeric_cells
    score = round(max(0, min(100, 100 * (.55 * completeness + .25 * uniqueness + .2 * (1 - outlier_rate)))))
    return {"score": score, "missing": missing, "duplicate_rows": duplicates["count"],
            "duplicate_percent": duplicates["percent"], "outliers": outliers,
            "datatype_issues": datatype_issues(frame)}


def correlation(record, method: str = "pearson") -> dict:
    if method not in {"pearson", "spearman", "kendall"}:
        raise AnalysisError(f"Unsupported correlation method: {method}")
    corr = correlation_matrix(record.frame, method=method)
    strong = []
    for i, left in enumerate(corr.columns):
        for right in corr.columns[i + 1:]:
            value = corr.loc[left, right]
            if pd.notna(value) and abs(value) >= STRONG_CORRELATION:
                strong.append({"left": left, "right": right, "value": round(float(value), 4),
                               "direction": "positive" if value >= 0 else "negative"})
    strong.sort(key=lambda item: abs(item["value"]), reverse=True)
    return {"columns": list(corr.columns), "matrix": [[finite(v) for v in row] for row in corr.to_numpy()],
            "strong": strong, "method": method}


def distribution(record, column: str) -> dict:
    frame = record.frame
    if column not in frame:
        raise AnalysisError(f"Unknown column: {column}")
    series = frame[column]
    values = series.dropna()
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        shape = numeric_distribution(series)
        skew = finite(shape["skewness"])
        if skew is None: descriptor = "not measurable"
        elif abs(skew) < .5: descriptor = "approximately symmetric"
        elif skew > 0: descriptor = "right-skewed (a tail of high values)"
        else: descriptor = "left-skewed (a tail of low values)"
        box = shape["box"] or {}
        outliers = iqr_outliers(series) if not values.empty else {"count": 0, "percent": 0.0}
        return {"kind": "numeric", "column": column,
                "statistics": {"mean": finite(shape["mean"]), "median": finite(shape["median"]),
                               "std": finite(shape["std"]), "skewness": skew, "count": int(values.count())},
                "histogram": {"counts": shape["counts"], "edges": [finite(v) for v in shape["edges"]]},
                "box": {k: finite(v) for k, v in box.items()},
                "outliers": {"count": outliers["count"], "percent": outliers["percent"]},
                "interpretation": f"{column} is {descriptor}. Median {finite(shape['median'])}, "
                                  f"mean {finite(shape['mean'])}, with {outliers['count']} IQR outliers."}
    entries = categorical_distribution(series)
    total = max(int(values.count()), 1)
    top = entries[0] if entries else None
    interpretation = (f"{column} has {int(series.nunique(dropna=True))} distinct values. "
                      f"'{top['value']}' is the most frequent at {top['proportion'] * 100:.1f}% of all rows."
                      if top else f"{column} has no non-null values.")
    return {"kind": "categorical", "column": column,
            "values": [{"label": e["value"], "count": e["count"], "proportion": e["proportion"]} for e in entries],
            "unique": int(series.nunique(dropna=True)), "total": total,
            "interpretation": interpretation}
