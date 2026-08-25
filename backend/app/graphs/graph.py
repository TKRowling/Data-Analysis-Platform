"""Sequential executor for the analysis pipeline.

Plain Python rather than a graph framework: the flow is linear, and keeping it dependency-free
matches the rest of the backend. Swap this executor for LangGraph without touching the nodes.
"""
from __future__ import annotations

from app.agents.base import AgentResult
from app.agents.orchestrator_agent import OrchestratorAgent
from app.graphs.nodes import PIPELINE
from app.graphs.state import AnalysisState


class AnalysisGraph:
    def __init__(self, orchestrator: OrchestratorAgent | None = None, client=None):
        self.orchestrator = orchestrator or OrchestratorAgent(client=client)

    def run(self, record, question: str) -> AgentResult:
        state = AnalysisState(record=record, question=question)
        for node in PIPELINE:
            state = node(state, self.orchestrator)
        state.result.trace = state.trace
        return state.result
