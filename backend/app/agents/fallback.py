"""Keyword routing used whenever the LLM planner is unavailable or produces an unusable plan.

This path keeps the platform fully functional with Ollama stopped. It is deliberately
deterministic so it can be tested exactly.
"""
from __future__ import annotations

import re

from app.agents.base import INTENT_OWNERS, AnalysisPlan, PlanColumns
from app.agents.column_resolver import mentioned_columns, resolve_column
from app.utils.dataframe_utils import categorical_columns, numeric_columns

METRIC_HINTS = ("revenue", "sale", "amount", "price", "value", "total", "income", "cost", "profit", "qty", "quantity")
GROUP_HINTS = ("product", "category", "region", "segment", "type", "name", "channel", "country", "city", "status")


def _features(question: str, numeric: list, target) -> list:
    """Predictor columns the question names explicitly, else every other numeric column."""
    named = [c for c in mentioned_columns(question, numeric) if c != target]
    return named[:10] if named else [c for c in numeric if c != target][:5]


def build_plan(record, question: str) -> AnalysisPlan:
    frame = record.frame
    q = question.lower()
    numeric = numeric_columns(frame)
    categorical = categorical_columns(frame)
    datetime_cols = [c for c in frame.columns if str(frame[c].dtype).startswith("datetime")]

    def plan(intent: str, columns: PlanColumns, **kwargs) -> AnalysisPlan:
        return AnalysisPlan(intent=intent, agent=INTENT_OWNERS.get(intent, "insight"),
                            columns=columns, source="fallback", **kwargs)

    if any(word in q for word in ("predict", "regression", "estimate")) and "forecast" not in q:
        target = resolve_column(q, numeric, METRIC_HINTS)
        if target:
            return plan("regression", PlanColumns(target=target, features=_features(q, numeric, target)))

    if any(word in q for word in ("classify", "classification", "which class", "churn")):
        target = resolve_column(q, categorical, GROUP_HINTS)
        if target:
            return plan("classification", PlanColumns(target=target, features=_features(q, numeric, target)))

    if "forecast" in q or "project" in q or "next month" in q or "future" in q:
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("forecast", PlanColumns(metric=metric, x=datetime_cols[0] if datetime_cols else None), chart="line")

    if "correlation" in q or "correlate" in q or "relationship" in q:
        pair = [c for c in mentioned_columns(q, numeric)][:2]
        if len(pair) == 2:
            return plan("correlation", PlanColumns(x=pair[0], y=pair[1]), chart="scatter")
        return plan("correlation", PlanColumns(), chart="heatmap")

    if "outlier" in q or "anomal" in q or "unusual" in q:
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("outlier", PlanColumns(metric=metric), chart="box")

    if "trend" in q or "over time" in q:
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric and datetime_cols:
            return plan("trend", PlanColumns(metric=metric, x=datetime_cols[0]), chart="line")

    if "segment" in q or "cohort" in q or "cluster" in q:
        group = resolve_column(q, categorical, GROUP_HINTS)
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if group:
            return plan("segmentation", PlanColumns(group=group, metric=metric), chart="bar")

    if any(word in q for word in ("top ", "highest", "largest", "best", "bottom", "lowest", "worst")):
        match = re.search(r"(?:top|bottom|first|last)\s+(\d+)", q)
        limit = min(int(match.group(1)), 50) if match else 5
        metric = resolve_column(q, numeric, METRIC_HINTS)
        group = resolve_column(q, categorical, GROUP_HINTS)
        if metric and group:
            return plan("ranking", PlanColumns(group=group, metric=metric), operation="sum", limit=limit, chart="bar")

    if any(word in q for word in ("average", "mean", "sum", "total", "count", "how many", "median")):
        if "average" in q or "mean" in q: operation = "mean"
        elif "median" in q: operation = "median"
        elif "count" in q or "how many" in q: operation = "count"
        else: operation = "sum"
        metric = resolve_column(q, numeric, METRIC_HINTS)
        group = next((c for c in mentioned_columns(q, categorical)), None)
        if metric:
            return plan("aggregation", PlanColumns(metric=metric, group=group), operation=operation,
                        chart="bar" if group else None)

    if any(word in q for word in ("distribution", "spread", "describe", "statistics", "summary of")):
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("descriptive", PlanColumns(metric=metric), chart="histogram")

    return plan("summary", PlanColumns())
