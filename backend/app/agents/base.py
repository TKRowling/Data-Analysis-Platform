"""Shared contract for the agent layer.

The invariant every agent upholds: ``data`` is produced by deterministic pandas/scipy
tools. A language model may choose *which* tool runs and may phrase ``answer``, but it
never supplies a figure.

Each agent declares its capabilities as ``Skill`` objects. A skill states the intent it
serves, the tool that computes it, and which plan slots must hold which kind of column.
That declaration is the single source of truth for three things: routing (which agent owns
an intent), validation (is this plan runnable), and the prompt shown to the planner model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

# Column slots a plan can fill. Skills declare which of these they need, and of what kind.
SLOTS = ("group", "metric", "x", "y", "target", "features")


@dataclass(frozen=True)
class Skill:
    """One capability of one agent.

    numeric / categorical / temporal name the slots that must hold a column of that kind.
    required names the slots that must be filled at all for the skill to run.
    """
    intent: str
    summary: str
    tool: str
    example: str
    required: tuple[str, ...] = ()
    numeric: tuple[str, ...] = ()
    categorical: tuple[str, ...] = ()
    temporal: tuple[str, ...] = ()
    chart: str | None = None

    def describe(self) -> dict[str, Any]:
        """Compact form handed to the planner model."""
        return {"intent": self.intent, "does": self.summary, "needs": list(self.required),
                "example": self.example}


class PlanColumns(BaseModel):
    group: str | None = None
    metric: str | None = None
    x: str | None = None
    y: str | None = None
    target: str | None = None
    features: list[str] = Field(default_factory=list)

    def named(self) -> list[str]:
        picked = [self.group, self.metric, self.x, self.y, self.target]
        return [c for c in picked if c] + list(self.features)


class AnalysisPlan(BaseModel):
    """The routing decision, from the language agent or the keyword fallback."""
    intent: str = "summary"
    agent: str = "insight"
    columns: PlanColumns = Field(default_factory=PlanColumns)
    operation: Literal["sum", "mean", "median", "min", "max", "count"] = "sum"
    limit: int = Field(default=5, ge=1, le=50)
    chart: str | None = None
    source: Literal["llm", "fallback"] = "fallback"
    # Slots the validator emptied because the model named ad column of the wrong kind.
    rejected: list[str] = Field(default_factory=list)

    def named_columns(self) -> list[str]:
        return self.columns.named()


@dataclass
class AgentResult:
    """The response shape returned to the client. These keys are the API contract."""
    agent: str
    intent: str
    answer: str
    data: dict[str, Any]
    suggested_chart: str | None = None
    verified: bool = True
    narration_source: str = "template"
    trace: list[dict] = field(default_factory=list)
    # Honest notes about the computation: auto-picked features, dropped rows, weak fits.
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent, "intent": self.intent, "answer": self.answer,
                "data": self.data, "suggested_chart": self.suggested_chart,
                "verified": self.verified, "narration_source": self.narration_source,
                "trace": self.trace, "caveats": self.caveats}


class Agent:
    """Base class for the four computing specialists.

    Subclasses declare ``skills`` and implement one handler per skill intent.
    """
    name: str = "agent"
    title: str = "Agent"
    role: str = ""
    skills: tuple[Skill, ...] = ()

    def handlers(self) -> dict[str, Callable]:  # pragma: no cover - interface
        raise NotImplementedError

    def skill(self, intent: str) -> Skill | None:
        return next((s for s in self.skills if s.intent == intent), None)

    def run(self, record, plan: AnalysisPlan) -> AgentResult:
        from app.core.exceptions import AnalysisError

        handler = self.handlers().get(plan.intent)
        if handler is None:
            raise AnalysisError(f"The {self.title.lower()} cannot handle '{plan.intent}'")
        return handler(record, plan)

    def describe(self) -> dict[str, Any]:
        return {"agent": self.name, "title": self.title, "role": self.role,
                "skills": [s.describe() for s in self.skills]}