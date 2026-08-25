"""Turns verified results into readable explanations, and answers open-ended summary questions.

The language model receives figures that pandas already computed and is asked only to phrase
them. If it is unavailable, or if it invents a number, the deterministic template stands.
"""
from __future__ import annotations

import json
import re

from app.agents.base import Agent, AgentResult, AnalysisPlan
from app.llm.prompt_loader import load_prompt
from app.services.eda_service import correlation, quality
from app.utils.dataframe_utils import categorical_columns, numeric_columns

MAX_NARRATION_CHARS = 900


class InsightAgent(Agent):
    name = "insight_agent"

    @staticmethod
    def summarize(text: str) -> str:
        return text.strip()

    def run(self, record, plan: AnalysisPlan) -> AgentResult:
        """Open-ended overview, used for 'summary' intent and anything unroutable."""
        frame = record.frame
        numeric, categorical = numeric_columns(frame), categorical_columns(frame)
        report = quality(record)
        links = correlation(record)["strong"][:3]
        highlights = [f"{item['left']} and {item['right']} (r = {item['value']})" for item in links]
        answer = (f"{record.name} holds {len(frame):,} rows across {len(frame.columns)} columns — "
                  f"{len(numeric)} numeric and {len(categorical)} categorical. Data quality scores "
                  f"{report['score']}/100 with {report['duplicate_rows']} duplicate rows and "
                  f"{len(report['missing'])} columns containing gaps."
                  + (f" The strongest relationships are {', '.join(highlights)}." if highlights else ""))
        return AgentResult(self.name, "summary", answer,
                           {"rows": len(frame), "columns": len(frame.columns),
                            "numeric_columns": numeric, "categorical_columns": categorical,
                            "quality_score": report["score"], "duplicate_rows": report["duplicate_rows"],
                            "columns_with_missing": len(report["missing"]), "strong_correlations": links},
                           None)

    def narrate(self, result: AgentResult, question: str, client) -> AgentResult:
        """Rephrase a verified result. Returns the result unchanged if the model is unavailable."""
        if client is None:
            return result
        payload = json.dumps(_shrink(result.data), default=str)[:2500]
        prompt = (f"Question: {question}\n"
                  f"Analysis performed: {result.intent}\n"
                  f"Verified result: {payload}\n"
                  f"Deterministic summary: {result.answer}\n\n"
                  "Explain this result.")
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


def _numbers(text: str) -> set[str]:
    return {token.replace(",", "").rstrip(".").lstrip("0") or "0" for token in NUMBER.findall(text)}


def _is_grounded(narration: str, result: AgentResult) -> bool:
    """Reject narration that introduces figures absent from the verified result.

    This is the last line of defence behind the prompt: the model may phrase, never compute.
    """
    if not narration or len(narration) < 10:
        return False
    allowed = _numbers(json.dumps(result.data, default=str)) | _numbers(result.answer)
    # Percentages and roundings of allowed values are tolerated; anything else is not.
    for token in _numbers(narration):
        if token in allowed:
            continue
        try:
            value = float(token)
        except ValueError:
            return False
        if any(abs(value - float(candidate)) < max(abs(value) * 0.01, 0.01)
               for candidate in allowed if _is_number(candidate)):
            continue
        return False
    return True


def _is_number(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def _shrink(data: dict) -> dict:
    """Trim row lists so the prompt stays inside the context window."""
    trimmed = {}
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 10:
            trimmed[key] = value[:10]
        elif key == "matrix":
            continue
        else:
            trimmed[key] = value
    return trimmed
