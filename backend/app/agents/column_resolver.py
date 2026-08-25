"""Match the words in a natural-language question to real dataframe columns."""
from __future__ import annotations

import pandas as pd

from app.utils.dataframe_utils import column_kind


def _normalize(name) -> str:
    return str(name).lower().replace("_", " ").strip()


def resolve_column(question: str, columns, keywords: tuple[str, ...] = ()):
    """Best-effort single column match. Longest exact mention wins, then keyword hints."""
    q = question.lower()
    exact = [c for c in columns if str(c).lower() in q]
    if exact:
        return max(exact, key=lambda c: len(str(c)))
    normalized = [c for c in columns if _normalize(c) in q]
    if normalized:
        return max(normalized, key=lambda c: len(str(c)))
    for word in keywords:
        for c in columns:
            if word in str(c).lower():
                return c
    return None


def mentioned_columns(question: str, columns) -> list:
    """Every column the question names, ordered by where it appears in the question."""
    q = question.lower()
    hits = []
    for c in columns:
        position = min((p for p in (q.find(str(c).lower()), q.find(_normalize(c))) if p != -1), default=-1)
        if position != -1:
            hits.append((position, c))
    return [c for _, c in sorted(hits)]


def describe_columns(frame: pd.DataFrame, limit: int = 60) -> list[dict]:
    """Compact column metadata for the LLM planner. Names and types only - never row values."""
    described = []
    for name in list(frame.columns)[:limit]:
        series = frame[name]
        entry = {"name": str(name), "kind": column_kind(series)}
        if entry["kind"] == "categorical":
            entry["distinct"] = int(series.nunique(dropna=True))
        described.append(entry)
    return described
