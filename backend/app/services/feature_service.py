"""Feature engineering: safe arithmetic expressions and named column transforms.

Expressions are evaluated by walking a restricted AST. Python's ``eval`` is never used, so a
formula cannot reach imports, attributes, calls, or builtins.
"""
from __future__ import annotations

import ast
import operator

import numpy as np
import pandas as pd

from app.core.exceptions import AnalysisError
from app.tools.feature_engineering.categorical_features import frequency_encode, one_hot_encode
from app.tools.feature_engineering.datetime_features import datetime_parts
from app.tools.feature_engineering.numeric_features import min_max_scale, standardize

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos}

MAX_NEW_COLUMNS = 40


def evaluate(node, frame: pd.DataFrame):
    if isinstance(node, ast.Expression): return evaluate(node.body, frame)
    if isinstance(node, ast.Name):
        if node.id not in frame: raise AnalysisError(f"Unknown column: {node.id}")
        return frame[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS: return OPS[type(node.op)](evaluate(node.left, frame), evaluate(node.right, frame))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS: return OPS[type(node.op)](evaluate(node.operand, frame))
    raise AnalysisError("Expression supports column names, numbers, and + - * / ** % only")


def _preview(frame: pd.DataFrame, name: str) -> list:
    return [None if pd.isna(v) else v for v in frame[name].head(10).tolist()]


def create_feature(record, name: str, expression: str) -> dict:
    """Add a calculated column from an arithmetic expression over existing columns."""
    if name in record.frame.columns:
        raise AnalysisError(f"Column '{name}' already exists — choose a different name")
    try:
        parsed = ast.parse(expression, mode="eval")
        result = evaluate(parsed, record.frame)
        record.frame[name] = result
    except AnalysisError:
        raise
    except SyntaxError as exc:
        raise AnalysisError(f"Could not parse the formula: {exc.msg}") from exc
    except Exception as exc:
        raise AnalysisError(f"Feature calculation failed: {exc}") from exc
    return {"name": name, "expression": expression, "type": str(record.frame[name].dtype),
            "created": [name], "sample": _preview(record.frame, name)}


def transform_feature(record, column: str, transform: str, name: str | None = None, bins: int = 4) -> dict:
    """Apply a named transform to an existing column, adding one or more new columns."""
    frame = record.frame
    if column not in frame:
        raise AnalysisError(f"Unknown column: {column}")
    series = frame[column]
    numeric_required = {"standardize", "min_max", "log", "bin"}
    if transform in numeric_required and not pd.api.types.is_numeric_dtype(series):
        raise AnalysisError(f"'{transform}' needs a numeric column; {column} is {series.dtype}")

    created: list[str] = []
    if transform == "standardize":
        target = name or f"{column}_z"
        frame[target] = standardize(series); created = [target]
    elif transform == "min_max":
        target = name or f"{column}_scaled"
        frame[target] = min_max_scale(series); created = [target]
    elif transform == "log":
        if (series.dropna() <= 0).any():
            raise AnalysisError(f"{column} contains values at or below zero, which have no logarithm")
        target = name or f"{column}_log"
        frame[target] = np.log(series); created = [target]
    elif transform == "bin":
        target = name or f"{column}_bin"
        try:
            frame[target] = pd.qcut(series, q=bins, duplicates="drop").astype(str)
        except ValueError as exc:
            raise AnalysisError(f"Could not split {column} into {bins} bins: {exc}") from exc
        created = [target]
    elif transform == "frequency":
        target = name or f"{column}_freq"
        frame[target] = frequency_encode(series); created = [target]
    elif transform == "one_hot":
        encoded = one_hot_encode(series, prefix=name or column)
        if len(encoded.columns) > MAX_NEW_COLUMNS:
            raise AnalysisError(f"{column} has {len(encoded.columns)} categories; one-hot encoding is capped at {MAX_NEW_COLUMNS}")
        for new_column in encoded.columns:
            frame[new_column] = encoded[new_column]
        created = list(encoded.columns)
    elif transform == "datetime_parts":
        parts = datetime_parts(series)
        if parts["year"].isna().all():
            raise AnalysisError(f"{column} could not be parsed as dates")
        for part in parts.columns:
            new_column = f"{name or column}_{part}"
            frame[new_column] = parts[part]
            created.append(new_column)
    else:
        raise AnalysisError(f"Unsupported transform: {transform}")

    return {"column": column, "transform": transform, "created": created,
            "type": str(frame[created[0]].dtype), "name": created[0],
            "sample": _preview(frame, created[0])}
