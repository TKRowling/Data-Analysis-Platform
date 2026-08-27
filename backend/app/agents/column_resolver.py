"""Match the words in a natural-language question to real dataframe columns.

Matching is anchored on word boundaries throughout. Plain substring matching produces
silent, hard-to-spot errors: a column named ``id`` matches "identify outliers", ``count``
matches "country", and ``sum`` matches "summary".
"""
from __future__ import annotations

import re

import pandas as pd

from app.utils.dataframe_utils import column_kind

KIND_ORDER = {"numeric": 0, "categorical": 1, "datetime": 2, "boolean": 3}
LOW_CARDINALITY = 50


def _normalize(name) -> str:
    return str(name).lower().replace("_", " ").strip()


def _pattern(text: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(text)}(?!\w)")


def mentions(question: str, *words: str) -> bool:
    """True when the question contains any of these words as whole words."""
    q = question.lower()
    return any(_pattern(word).search(q) for word in words)


def _find(question: str, column) -> int:
    """Position of a whole-word mention of the column, or -1."""
    q = question.lower()
    positions = []
    for form in (str(column).lower(), _normalize(column)):
        match = _pattern(form).search(q)
        if match:
            positions.append(match.start())
    return min(positions) if positions else -1


def resolve_column(question: str, columns, keywords: tuple[str, ...] = ()):
    """Best-effort single column match: longest whole-word mention, then keyword hints."""
    named = [c for c in columns if _find(question, c) != -1]
    if named:
        return max(named, key=lambda c: len(str(c)))
    for word in keywords:
        hits = [c for c in columns if _pattern(word).search(_normalize(c))]
        if hits:
            return max(hits, key=lambda c: len(str(c)))
    return None


def mentioned_columns(question: str, columns) -> list:
    """Every column the question names, ordered by where it appears in the question."""
    hits = [(_find(question, c), c) for c in columns]
    return [c for position, c in sorted(h for h in hits if h[0] != -1)]


def describe_columns(frame: pd.DataFrame, limit: int = 60) -> dict:
    """Column metadata for the planner model. Names and types only — never row values.

    Columns are ordered numeric first, then low-cardinality categoricals, then the rest, so
    that when a wide frame is truncated the planner still sees the columns it is most
    likely to need. Truncation is reported rather than silent.
    """
    entries = []
    for name in frame.columns:
        series = frame[name]
        kind = column_kind(series)
        entry = {"name": str(name), "kind": kind}
        distinct = None
        if kind in {"categorical", "boolean"}:
            distinct = int(series.nunique(dropna=True))
            entry["distinct"] = distinct
        rank = (KIND_ORDER.get(kind, 9),
                0 if distinct is None or distinct <= LOW_CARDINALITY else 1)
        entries.append((rank, entry))

    entries.sort(key=lambda item: item[0])
    shown = [entry for _, entry in entries[:limit]]
    return {"columns": shown, "total": len(frame.columns), "truncated": len(frame.columns) > limit}