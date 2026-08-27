"""Insight generation agent.

Two jobs:

1. ``run`` answers open-ended "tell me about this data" questions, and is the safe landing
   spot when no specialist can serve a plan.
2. ``narrate`` takes a result another agent already computed and asks the language model to
   phrase it. The model is given finished numbers and is never asked to derive one. If its
   sentence contains a figure that is not in the verified result, the sentence is discarded.

This module depends only on ``app.tools`` — never on ``app.services`` — so the dependency
arrow keeps pointing downward.
"""
from __future__ import annotations

import json
import re

from app.agents.base import Agent, AgentResult, AnalysisPlan, Skill
from app.llm.prompt_loader import load_prompt
from app.tools.correlation.correlation import correlation_matrix
from app.tools.correlation.thresholds import STRONG, direction, strength
from app.tools.quality import duplicate_summary, missing_summary
from app.utils.dataframe_utils import categorical_columns, finite, numeric_columns

MAX_NARRATION_CHARS = 900
MAX_PROMPT_CHARS = 2500
MAX_ROWS_IN_PROMPT = 10
BULKY_KEYS = {"matrix", "points", "histogram"}
ROUNDING_TOLERANCE = 0.01


class InsightAgent(Agent):
    name = "insight_agent"
    title = "Insight generation agent"
    role = "Summarises a dataset and explains verified results in plain language."

    skills = (
        Skill(
            intent="summary",
            summary="Overall shape, quality, and strongest relationships in the dataset.",
            tool="tools.quality + tools.correlation",
            example="Give me an overview of this dataset.",
        ),
    )

    def handlers(self):
        return {"summary": self.run}

    def run(self, record, plan: AnalysisPlan | None = None) -> AgentResult:
        frame = record.frame
        numeric, categorical = numeric_columns(frame), categorical_columns(frame)
        missing = missing_summary(frame)
        duplicates = duplicate_summary(frame)

        links = []
        if len(numeric) >= 2:
            corr = correlation_matrix(frame)
            for index, a in enumerate(corr.columns):
                for b in corr.columns[index + 1:]:
                    value = finite(corr.loc[a, b])
                    if value is not None and abs(value) >= STRONG:
                        links.append({"left": a, "right": b, "value": value,
                                      "strength": strength(value), "direction": direction(value)})
            links.sort(key=lambda item: abs(item["value"]), reverse=True)
        top_links = links[:3]

        answer = (f"{record.name} holds {len(frame):,} rows across {len(frame.columns)} columns — "
                  f"{len(numeric)} numeric and {len(categorical)} categorical. "
                  f"There are {duplicates['count']:,} duplicate rows and {len(missing)} columns "
                  "containing gaps.")
        if top_links:
            phrased = ", ".join(f"{item['left']} and {item['right']} (r = {item['value']})"
                                for item in top_links)
            answer += f" The strongest relationships are {phrased}."
        else:
            answer += " No pair of numeric columns is strongly correlated."

        return AgentResult(self.name, "summary", answer,
                           {"rows": int(len(frame)), "columns": int(len(frame.columns)),
                            "numeric_columns": numeric, "categorical_columns": categorical,
                            "duplicate_rows": duplicates["count"],
                            "columns_with_missing": len(missing),
                            "strong_correlations": top_links},
                           None)

    # ----------------------------------------------------------------- narration
    def narrate(self, result: AgentResult, question: str, client) -> AgentResult:
        """Rephrase a verified result. Returns it untouched if that cannot be done safely."""
        if client is None:
            return result
        payload = json.dumps(_shrink(result.data), default=str)[:MAX_PROMPT_CHARS]
        caveats = " ".join(result.caveats)
        prompt = (f"Question: {question}\n"
                  f"Analysis performed: {result.intent}\n"
                  f"Verified result: {payload}\n"
                  f"Deterministic summary: {result.answer}\n"
                  + (f"Caveats you must preserve: {caveats}\n" if caveats else "")
                  + "\nExplain this result.")
        try:
            narration = client.complete(prompt, system=load_prompt("insight")).strip()
        except Exception:
            return result
        if not _is_grounded(narration, result):
            return result
        result.answer = narration[:MAX_NARRATION_CHARS]
        result.narration_source = "llm"
        return result


NUMBER = re.compile(r"-?\d[\d,]*\.?\d*")


def _tokens(text: str) -> set[str]:
    return {token.replace(",", "").rstrip(".") for token in NUMBER.findall(text)}


def _as_float(token: str) -> float | None:
    try:
        return float(token)
    except ValueError:
        return None


def _is_grounded(narration: str, result: AgentResult) -> bool:
    """Reject narration that introduces a figure absent from the verified result.

    The last line of defence behind the prompt: the model may phrase, never compute.
    Rounding within 1% of an allowed value is tolerated; anything else fails the check.
    """
    if not narration or len(narration) < 10:
        return False
    source = json.dumps(result.data, default=str) + " " + result.answer + " " + " ".join(result.caveats)
    allowed = [v for v in (_as_float(t) for t in _tokens(source)) if v is not None]
    for token in _tokens(narration):
        value = _as_float(token)
        if value is None:
            return False
        tolerance = max(abs(value) * ROUNDING_TOLERANCE, ROUNDING_TOLERANCE)
        if not any(abs(value - candidate) <= tolerance for candidate in allowed):
            return False
    return True


def _shrink(data: dict) -> dict:
    """Trim the payload so the prompt stays inside the context window.

    Bulky keys are checked before the generic list check, so a large matrix is dropped
    rather than truncated into the prompt.
    """
    trimmed = {}
    for key, value in data.items():
        if key in BULKY_KEYS:
            continue
        if isinstance(value, list) and len(value) > MAX_ROWS_IN_PROMPT:
            trimmed[key] = value[:MAX_ROWS_IN_PROMPT]
            trimmed[f"{key}_truncated_from"] = len(value)
        else:
            trimmed[key] = value
    return trimmed