"""Deterministic keyword routing.

Used whenever the language agent is unavailable or produces an unusable plan. This path
keeps the platform fully functional with Ollama stopped, so it is deliberately simple and
exactly testable.

All matching goes through ``mentions``/``resolve_column``, which are anchored on word
boundaries. Substring matching silently mis-routes: "sum" fires inside "summary", "count"
inside "country" and "discount", "id" inside "identify".
"""
from __future__ import annotations

import re

import pandas as pd

from app.agents.base import PlanColumns
from app.agents.column_resolver import mentioned_columns, mentions, resolve_column
from app.agents.validation import validate_plan
from app.utils.dataframe_utils import categorical_columns, numeric_columns

METRIC_HINTS = ("revenue", "sales", "sale", "amount", "price", "value", "income",
                "cost", "profit", "quantity", "qty", "total")
GROUP_HINTS = ("product", "category", "region", "segment", "channel", "country",
               "city", "status", "type", "name")

COUNT_PHRASES = ("count", "how many", "number of")
MEAN_PHRASES = ("average", "mean", "typical")
SUM_PHRASES = ("sum", "total", "combined")

# Checked in order. The first matching rule wins.
PREDICT_WORDS = ("predict", "regression", "estimate")
CLASSIFY_WORDS = ("classify", "classification", "churn")
FORECAST_WORDS = ("forecast", "project", "projection", "future")
CORRELATION_WORDS = ("correlation", "correlate", "correlated", "relationship", "related")
OUTLIER_WORDS = ("outlier", "outliers", "anomaly", "anomalies", "unusual", "extreme")
TREND_WORDS = ("trend", "over time", "trajectory")
SEGMENT_WORDS = ("segment", "segments", "cohort", "cohorts", "cluster", "clusters", "breakdown")
RANK_WORDS = ("top", "highest", "largest", "best", "bottom", "lowest", "worst", "rank")
SPREAD_WORDS = ("distribution", "spread", "describe", "statistics", "histogram", "variance")
OVERVIEW_WORDS = ("summary", "summarise", "summarize", "overview", "tell me about", "what is in")

LIMIT = re.compile(r"(?:top|bottom|first|last)\s+(\d+)")


def build_plan(record, question: str):
    """Classify a question with keywords alone and return a validated plan."""
    frame = record.frame
    q = question.lower()
    numeric = numeric_columns(frame)
    categorical = [c for c in categorical_columns(frame)
                   if not pd.api.types.is_datetime64_any_dtype(frame[c])]
    temporal = [c for c in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[c])]

    def plan(intent: str, columns: PlanColumns, **kwargs):
        return validate_plan(frame, intent, columns, source="fallback", **kwargs)

    def features_for(target):
        named = [c for c in mentioned_columns(q, numeric) if c != target]
        return named[:10]

    # An explicit request for an overview must not be captured by the aggregation rule below.
    if mentions(q, *OVERVIEW_WORDS) and not mentions(q, *SEGMENT_WORDS) and not mentions(q, *RANK_WORDS):
        return plan("summary", PlanColumns())

    if mentions(q, *PREDICT_WORDS) and not mentions(q, *FORECAST_WORDS):
        target = resolve_column(q, numeric, METRIC_HINTS)
        if target:
            return plan("regression", PlanColumns(target=target, features=features_for(target)))

    if mentions(q, *CLASSIFY_WORDS):
        target = resolve_column(q, categorical, GROUP_HINTS)
        if target:
            return plan("classification", PlanColumns(target=target, features=features_for(target)))

    if mentions(q, *FORECAST_WORDS):
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("forecast", PlanColumns(metric=metric, x=temporal[0] if temporal else None))

    if mentions(q, *CORRELATION_WORDS):
        pair = mentioned_columns(q, numeric)[:2]
        if len(pair) == 2:
            return plan("correlation", PlanColumns(x=pair[0], y=pair[1]))
        return plan("correlation", PlanColumns(), chart="heatmap")

    if mentions(q, *OUTLIER_WORDS):
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("outlier", PlanColumns(metric=metric))

    if mentions(q, *TREND_WORDS) and temporal:
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("trend", PlanColumns(metric=metric, x=temporal[0]))

    if mentions(q, *SEGMENT_WORDS):
        group = resolve_column(q, categorical, GROUP_HINTS)
        if group:
            return plan("segmentation", PlanColumns(group=group,
                                                    metric=resolve_column(q, numeric, METRIC_HINTS)))

    if mentions(q, *RANK_WORDS):
        match = LIMIT.search(q)
        limit = min(int(match.group(1)), 50) if match else 5
        metric = resolve_column(q, numeric, METRIC_HINTS)
        group = resolve_column(q, categorical, GROUP_HINTS)
        if metric and group:
            return plan("ranking", PlanColumns(group=group, metric=metric),
                        operation="sum", limit=limit)

    if mentions(q, *MEAN_PHRASES, *SUM_PHRASES, *COUNT_PHRASES, "median"):
        if mentions(q, *MEAN_PHRASES):
            operation = "mean"
        elif mentions(q, "median"):
            operation = "median"
        elif mentions(q, *COUNT_PHRASES):
            operation = "count"
        else:
            operation = "sum"
        metric = resolve_column(q, numeric, METRIC_HINTS)
        group = next(iter(mentioned_columns(q, categorical)), None)
        if metric:
            return plan("aggregation", PlanColumns(metric=metric, group=group), operation=operation)

    if mentions(q, *SPREAD_WORDS):
        metric = resolve_column(q, numeric, METRIC_HINTS)
        if metric:
            return plan("descriptive", PlanColumns(metric=metric))

    return plan("summary", PlanColumns())