"""Shared contract for the agent layer.

The invariant every agent upholds: ``data`` is produced by deterministic pandas/scipy
tools. A language model may choose *which* tool runs and may phrase ``answer``, but it
never supplies a figure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["statistical", "pattern", "predictive", "insight"]

# Which specialist owns which intent. Used by both the LLM planner and the fallback router.
INTENT_OWNERS: dict[str, str] = {
    "aggregation": "statistical",
    "ranking": "statistical",
    "descriptive": "statistical",
    "outlier": "statistical",
    "correlation": "pattern",
    "relationship": "pattern",
    "segmentation": "pattern",
    "trend": "pattern",
    "regression": "predictive",
    "classification": "predictive",
    "forecast": "predictive",
    "summary": "insight",
}


class PlanColumns(BaseModel):
    group: str | None = None
    metric: str | None = None
    x: str | None = None
    y: str | None = None
    target: str | None = None
    features: list[str] = Field(default_factory=list)


class AnalysisPlan(BaseModel):
    """The routing decision. Produced by the LLM, or by the keyword fallback."""
    intent: str = "summary"
    agent: str = "insight"
    columns: PlanColumns = Field(default_factory=PlanColumns)
    operation: Literal["sum", "mean", "median", "min", "max", "count"] = "sum"
    limit: int = Field(default=5, ge=1, le=50)
    chart: str | None = None
    source: Literal["llm", "fallback"] = "fallback"

    def named_columns(self) -> list[str]:
        picked = [self.columns.group, self.columns.metric, self.columns.x, self.columns.y, self.columns.target]
        return [c for c in picked if c] + list(self.columns.features)


@dataclass
class AgentResult:
    """The response shape returned to the client. Keys here are part of the API contract."""
    agent: str
    intent: str
    answer: str
    data: dict[str, Any]
    suggested_chart: str | None = None
    verified: bool = True
    narration_source: str = "template"
    trace: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent, "intent": self.intent, "answer": self.answer, "data": self.data,
                "suggested_chart": self.suggested_chart, "verified": self.verified,
                "narration_source": self.narration_source, "trace": self.trace}


class Agent:
    """Base class for the four specialists."""
    name: str = "agent"

    def run(self, record, plan: AnalysisPlan) -> AgentResult:  # pragma: no cover - interface
        raise NotImplementedError
