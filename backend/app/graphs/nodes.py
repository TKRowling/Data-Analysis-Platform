"""The four stages of an AI analysis: understand, delegate, compute, narrate."""
from __future__ import annotations

import logging

from app.core.exceptions import AnalysisError
from app.graphs.routing import label, select
from app.graphs.state import AnalysisState

logger = logging.getLogger(__name__)


def understand(state: AnalysisState, orchestrator) -> AnalysisState:
    """Turn the question into a validated routing plan."""
    state.plan = orchestrator.plan(state.record, state.question)
    source = "language model" if state.plan.source == "llm" else "keyword routing"
    state.log("understand", "orchestrator_agent",
              f"Interpreted the question as '{state.plan.intent}' using {source}.")
    return state


def delegate(state: AnalysisState, orchestrator) -> AnalysisState:
    """Pick the specialist that owns the plan's intent."""
    state.plan.agent = select(state.plan)
    columns = ", ".join(state.plan.named_columns()) or "no specific columns"
    state.log("delegate", "orchestrator_agent",
              f"Delegated to the {label(state.plan.agent)} with {columns}.")
    return state


def compute(state: AnalysisState, orchestrator) -> AnalysisState:
    """Run the specialist. Every figure in the result originates here, from pandas."""
    try:
        state.result = orchestrator.dispatch(state.record, state.plan)
    except AnalysisError:
        # The specialist could not work with this plan - fall back to a dataset summary
        # rather than failing the request outright.
        if state.plan.intent == "summary":
            raise
        state.log("compute", f"{state.plan.agent}_agent",
                  "Could not complete that analysis; answering with a dataset summary instead.")
        state.plan.intent, state.plan.agent = "summary", "insight"
        state.result = orchestrator.insight.run(state.record, state.plan)
        return state
    state.log("compute", state.result.agent, f"Computed the {state.result.intent} result with pandas.")
    return state


def narrate(state: AnalysisState, orchestrator) -> AnalysisState:
    """Let the insight agent phrase the verified numbers, if a model is available."""
    before = state.result.answer
    state.result = orchestrator.insight.narrate(state.result, state.question, orchestrator.client)
    if state.result.narration_source == "llm":
        state.log("narrate", "insight_agent", "Explained the verified figures using the language model.")
    elif before:
        state.log("narrate", "insight_agent", "Used the deterministic explanation.")
    return state


PIPELINE = (understand, delegate, compute, narrate)
