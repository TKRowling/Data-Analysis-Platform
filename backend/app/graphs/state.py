"""State carried through the LangGraph analysis pipeline.

Nodes return partial updates. Two channels carry history, and they are deliberately
different things:

``trace``  is per-question scratch — the hand-off trail behind one answer. Additive within
           a question, and reset at the start of the next one by sending ``None``.
``turns``  is the conversation memory. It survives across questions on the same thread,
           bounded to the most recent ``MEMORY_TURNS`` exchanges.

The live dataframe is deliberately *not* in the state. Every state channel is serialized
into the checkpoint after each node, a DataFrame is not serializable at all, and even if it
were we would be copying the whole frame once per superstep. It travels in the run config
instead; see ``dataset_of``.
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from app.agents.base import AgentResult, AnalysisPlan
from app.core.exceptions import AnalysisError

# How many past exchanges a conversation remembers. Older ones fall off the front, which
# bounds both the checkpoint size and the prompt the planner sees.
MEMORY_TURNS = 6


class Turn(TypedDict):
    """One finished exchange — small enough to checkpoint and to put in a prompt."""
    question: str
    intent: str
    agent: str
    answer: str


def append_steps(existing: list[dict] | None, incoming: list[dict] | None) -> list[dict]:
    """Additive trace, resettable: sending ``None`` starts a fresh trail."""
    if incoming is None:
        return []
    return (existing or []) + list(incoming)


def remember(existing: list[Turn] | None, incoming: list[Turn] | None) -> list[Turn]:
    """Append finished exchanges, keeping only the most recent ones. ``None`` forgets."""
    if incoming is None:
        return []
    return ((existing or []) + list(incoming))[-MEMORY_TURNS:]


class AnalysisState(TypedDict, total=False):
    # Input for this question
    question: str

    # Produced along the way — scratch, replaced on every question
    plan: AnalysisPlan
    result: AgentResult
    error: str
    trace: Annotated[list[dict], append_steps]

    # Conversation memory — survives across questions on the same thread
    turns: Annotated[list[Turn], remember]


def step(stage: str, agent: str, detail: str) -> dict:
    """A single trace entry. The UI renders these as the agent hand-off trail."""
    return {"stage": stage, "agent": agent, "detail": detail}


def dataset_of(config) -> Any:
    """The live DatasetRecord for this run.

    Carried in the run config rather than the state so it never reaches the checkpointer.
    """
    record = ((config or {}).get("configurable") or {}).get("record")
    if record is None:
        raise AnalysisError("No dataset was supplied to the analysis graph")
    return record
