"""Classifies a question and delegates calculation to a specialist.

Planning is hybrid: the language model reads the question and the column list and proposes a
routing plan. Anything it proposes is validated against the real dataframe. If the model is
unreachable, returns unusable JSON, or names a column that does not exist, a deterministic
keyword router takes over. Either way a specialist computes the answer with pandas.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, field_validator

from app.agents.base import INTENT_OWNERS, AnalysisPlan, PlanColumns
from app.agents.column_resolver import describe_columns
from app.agents.fallback import build_plan
from app.agents.insight_agent import InsightAgent
from app.agents.pattern_agent import PatternAgent
from app.agents.predictive_agent import PredictiveAgent
from app.agents.statistical_agent import StatisticalAgent
from app.llm.prompt_loader import load_prompt
from app.llm.structured_output import parse_structured

logger = logging.getLogger(__name__)

VALID_OPERATIONS = {"sum", "mean", "median", "min", "max", "count"}
VALID_CHARTS = {"bar", "line", "scatter", "histogram", "box", "pie", "heatmap"}


class LLMPlan(BaseModel):
    """What the planner model is asked to return. Deliberately lenient - it is validated after."""
    intent: str = "summary"
    columns: PlanColumns = Field(default_factory=PlanColumns)
    operation: str = "sum"
    limit: int = 5
    chart: str | None = None

    @field_validator("columns", mode="before")
    @classmethod
    def _default_columns(cls, value):
        return value if isinstance(value, dict) else PlanColumns()

    @field_validator("intent", "operation", mode="before")
    @classmethod
    def _clean_text(cls, value):
        return str(value).strip().lower() if value else ""

    @field_validator("limit", mode="before")
    @classmethod
    def _clean_limit(cls, value):
        try:
            return max(1, min(int(value), 50))
        except (TypeError, ValueError):
            return 5


class OrchestratorAgent:
    """Classifies a natural-language request and delegates calculation to a specialist."""

    def __init__(self, client=None):
        self.client = client
        self.statistical = StatisticalAgent()
        self.pattern = PatternAgent()
        self.predictive = PredictiveAgent()
        self.insight = InsightAgent()
        self.specialists = {"statistical": self.statistical, "pattern": self.pattern,
                            "predictive": self.predictive, "insight": self.insight}

    def route(self, question: str) -> str:
        """Keyword classification of a question into an agent family."""
        query = question.lower()
        if any(word in query for word in ("predict", "forecast", "classify")): return "predictive"
        if any(word in query for word in ("correlation", "relationship", "trend", "segment")): return "pattern"
        if any(word in query for word in ("average", "mean", "sum", "top", "outlier")): return "statistical"
        return "insight"

    def plan(self, record, question: str) -> AnalysisPlan:
        """Ask the model for a routing plan, validate it, and fall back on any problem."""
        if self.client is not None:
            try:
                return self._validated_llm_plan(record, question)
            except Exception as exc:
                logger.info("LLM planning unavailable, using keyword routing: %s", exc)
        return build_plan(record, question)

    def _validated_llm_plan(self, record, question: str) -> AnalysisPlan:
        columns = describe_columns(record.frame)
        prompt = (f"Columns available:\n{json.dumps(columns)}\n\n"
                  f"Question: {question}\n\nReturn the routing plan as JSON.")
        proposed = parse_structured(self.client, prompt, load_prompt("orchestrator"), LLMPlan)

        intent = proposed.intent if proposed.intent in INTENT_OWNERS else "summary"
        available = set(record.frame.columns)
        picked = proposed.columns.model_dump()
        for key in ("group", "metric", "x", "y", "target"):
            if picked.get(key) not in available:
                picked[key] = None
        picked["features"] = [c for c in picked.get("features", []) if c in available]

        resolved = AnalysisPlan(
            intent=intent,
            agent=INTENT_OWNERS.get(intent, "insight"),
            columns=PlanColumns(**picked),
            operation=proposed.operation if proposed.operation in VALID_OPERATIONS else "sum",
            limit=proposed.limit,
            chart=proposed.chart if proposed.chart in VALID_CHARTS else None,
            source="llm",
        )
        # A plan that named nothing usable is no better than the keyword router's guess.
        if intent != "summary" and not resolved.named_columns():
            fallback = build_plan(record, question)
            if fallback.named_columns():
                return fallback
        return resolved

    def dispatch(self, record, plan: AnalysisPlan):
        """Run the specialist that owns this plan's intent."""
        specialist = self.specialists.get(plan.agent, self.insight)
        return specialist.run(record, plan)
