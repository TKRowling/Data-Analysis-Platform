"""The multi-agent analysis graph, built with LangGraph.

    START
      |
    understand        natural language agent reads the question -> AnalysisPlan
      |
    delegate          announces the hand-off
      |
      +--- conditional on plan.agent ---+
      |            |          |         |
 statistical   pattern   predictive  insight        (one specialist computes)
      |            |          |         |
      +--- conditional on error --------+
      |                                 |
   recover  ------------------------> narrate       (insight agent phrases the result)
                                        |
                                       END

The graph is linear per request but genuinely branching: the specialist chosen depends on
the plan, and a specialist that cannot run its plan is routed to ``recover`` rather than
failing the request. Adding a sixth agent means adding a Skill, a node, and one entry in
the conditional map — no other file changes.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.base import AgentResult
from app.agents.language_agent import LanguageAgent
from app.agents.registry import AGENTS, build_agents
from app.graphs.nodes import SPECIALIST_NODES, after_compute, build_nodes, choose_specialist
from app.graphs.state import AnalysisState


class AnalysisGraph:
    """Compiles and runs the agent graph for one dataset question."""

    def __init__(self, language_agent: LanguageAgent | None = None, client=None,
                 agents: dict | None = None):
        self.language_agent = language_agent or LanguageAgent(client=client)
        self.agents = agents or AGENTS
        self.compiled = self._compile()

    def _compile(self):
        nodes = build_nodes(self.language_agent, self.agents)
        builder = StateGraph(AnalysisState)

        for name, node in nodes.items():
            builder.add_node(name, node)

        builder.add_edge(START, "understand")
        builder.add_edge("understand", "delegate")
        builder.add_conditional_edges(
            "delegate", choose_specialist, {key: key for key in SPECIALIST_NODES})

        for key in SPECIALIST_NODES:
            builder.add_conditional_edges(
                key, after_compute, {"recover": "recover", "narrate": "narrate"})

        builder.add_edge("recover", "narrate")
        builder.add_edge("narrate", END)
        return builder.compile()

    def run(self, record, question: str) -> AgentResult:
        final = self.compiled.invoke({"record": record, "question": question, "trace": []})
        result: AgentResult = final["result"]
        # Number the steps at the end so the UI does not depend on node execution order.
        result.trace = [{**entry, "step": index}
                        for index, entry in enumerate(final.get("trace", []), start=1)]
        return result

    def mermaid(self) -> str:
        """Diagram source for the docs. Useful when the graph grows past four specialists."""
        return self.compiled.get_graph().draw_mermaid()


def fresh_graph(client=None) -> AnalysisGraph:
    """A graph with its own agent instances — handy in tests to avoid shared state."""
    return AnalysisGraph(client=client, agents=build_agents())