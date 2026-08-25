"""State carried through the analysis graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentResult, AnalysisPlan


@dataclass
class AnalysisState:
    record: Any
    question: str
    plan: AnalysisPlan | None = None
    result: AgentResult | None = None
    trace: list[dict] = field(default_factory=list)

    def log(self, stage: str, agent: str, detail: str) -> None:
        self.trace.append({"step": len(self.trace) + 1, "stage": stage, "agent": agent, "detail": detail})
