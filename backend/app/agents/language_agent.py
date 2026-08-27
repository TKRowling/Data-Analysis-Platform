"""Natural language agent — the delegator.

Reads the user's question and decides which specialist should handle it and with which
columns. It performs no calculation of any kind.

The model is shown two things only: the skill menu (what the specialists can do) and the
column metadata (names and kinds — never row values). Whatever it proposes is validated
against the real dataframe before anything runs. On any failure — connection error,
unparseable JSON, an invented column, a column of the wrong kind — the deterministic
keyword router takes over and the question is still answered.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, field_validator

from app.agents.base import AnalysisPlan, PlanColumns
from app.agents.column_resolver import describe_columns
from app.agents.fallback import build_plan
from app.agents.registry import skill_menu
from app.agents.validation import is_runnable, validate_plan
from app.llm.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class LLMPlan(BaseModel):
    """What the planner model is asked to return. Lenient here; validated afterwards."""
    intent: str = "summary"
    columns: PlanColumns = Field(default_factory=PlanColumns)
    operation: str = "sum"
    limit: int = 5
    chart: str | None = None
    reasoning: str = ""

    @field_validator("columns", mode="before")
    @classmethod
    def _default_columns(cls, value):
        return value if isinstance(value, dict) else PlanColumns()

    @field_validator("intent", "operation", mode="before")
    @classmethod
    def _clean_text(cls, value):
        return str(value).strip().lower() if value else ""

    @field_validator("chart", mode="before")
    @classmethod
    def _clean_chart(cls, value):
        if value in (None, "", "null", "none"):
            return None
        return str(value).strip().lower()

    @field_validator("limit", mode="before")
    @classmethod
    def _clean_limit(cls, value):
        try:
            return max(1, min(int(value), 50))
        except (TypeError, ValueError):
            return 5


class LanguageAgent:
    """Turns a question into a validated, runnable AnalysisPlan."""

    name = "language_agent"
    title = "Natural language agent"
    role = "Understands the question and delegates it to the right specialist."

    def __init__(self, client=None):
        self.client = client

    def plan(self, record, question: str) -> AnalysisPlan:
        if self.client is not None:
            try:
                proposed = self._llm_plan(record, question)
                if is_runnable(proposed):
                    return proposed
                logger.info("LLM plan for %r was not runnable (rejected: %s); using keyword routing",
                            question, proposed.rejected)
            except Exception as exc:
                logger.info("LLM planning unavailable (%s); using keyword routing", exc)
        return build_plan(record, question)

    def _llm_plan(self, record, question: str) -> AnalysisPlan:
        from app.llm.structured_output import parse_structured

        described = describe_columns(record.frame)
        prompt = (
            f"Available analyses:\n{json.dumps(skill_menu(), indent=None)}\n\n"
            f"Dataset columns ({described['total']} total"
            f"{', truncated to the most relevant' if described['truncated'] else ''}):\n"
            f"{json.dumps(described['columns'])}\n\n"
            f"Question: {question}\n\n"
            "Return the routing plan as JSON."
        )
        proposed = parse_structured(self.client, prompt, load_prompt("orchestrator"), LLMPlan)
        plan = validate_plan(record.frame, proposed.intent, proposed.columns,
                             operation=proposed.operation, limit=proposed.limit,
                             chart=proposed.chart, source="llm")
        if plan.rejected:
            logger.info("Discarded unusable slots from the LLM plan: %s", plan.rejected)
        return plan

    def classify(self, record, question: str) -> str:
        """Which specialist would handle this question. Deterministic; used for display."""
        return build_plan(record, question).agent


# Backwards-compatible alias. The old name described the class less accurately than the
# spec's own term ("natural language agent"), but existing imports keep working.
OrchestratorAgent = LanguageAgent