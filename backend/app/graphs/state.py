"""State carried through the LangGraph analysis pipeline.

Nodes return partial updates. ``trace`` uses an additive reducer so each node appends its
own step without needing to read the existing list.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.agents.base import AgentResult, AnalysisPlan


class AnalysisState(TypedDict, total=False):
    # Inputs
    record: Any                 # DatasetRecord — carries the live dataframe
    question: str

    # Produced along the way
    plan: AnalysisPlan
    result: AgentResult
    error: str                  # set by a specialist that could not run its plan
    trace: Annotated[list[dict], operator.add]


def step(stage: str, agent: str, detail: str) -> dict:
    """A single trace entry. The UI renders these as the agent hand-off trail."""
    return {"stage": stage, "agent": agent, "detail": detail}