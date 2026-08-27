"""The nodes of the analysis graph, and the two functions that route between them.

A node takes the state plus the run config and returns a *partial* update. ``trace`` is
additive (see ``state.py``), so a node appends its own step without reading the existing
list. The dataframe comes from the config rather than the state, because state is
checkpointed and a dataframe cannot be.

The specialists are built from the agent registry rather than listed by hand: adding a
fifth agent means adding it to ``build_agents`` — the node, the conditional edge, and the
routing map all follow. ``graph.py`` wires these together.
"""
from __future__ import annotations

import logging

from app.agents.base import Agent
from app.agents.language_agent import LanguageAgent
from app.agents.registry import AGENTS
from app.core.exceptions import AnalysisError
from app.graphs.state import AnalysisState, Turn, dataset_of, step

logger = logging.getLogger(__name__)

# One node per computing specialist. The keys are both node names and the values
# ``choose_specialist`` returns, so they must match the registry's agent keys.
SPECIALIST_NODES: tuple[str, ...] = tuple(AGENTS)

# The specialist that answers when a plan cannot be run as written.
FALLBACK_NODE = "insight"

# How many past exchanges the planner is shown. The state keeps more than the prompt uses.
HISTORY_IN_PROMPT = 3


def label(agents: dict[str, Agent], key: str) -> str:
    """Human name of a specialist, for the trace the UI renders."""
    agent = agents.get(key)
    return agent.title.lower() if agent else f"{key} agent"


def choose_specialist(state: AnalysisState) -> str:
    """Conditional edge out of ``delegate``: which specialist owns this plan."""
    plan = state.get("plan")
    agent = plan.agent if plan else FALLBACK_NODE
    if agent not in SPECIALIST_NODES:
        logger.info("Plan named unknown agent %r; using %s", agent, FALLBACK_NODE)
        return FALLBACK_NODE
    return agent


def after_compute(state: AnalysisState) -> str:
    """Conditional edge out of every specialist: recover from a failure, or narrate."""
    return "recover" if state.get("error") else "narrate"


def build_nodes(language_agent: LanguageAgent, agents: dict[str, Agent]) -> dict:
    """Every node of the graph, keyed by node name, bound to these agent instances."""
    insight = agents[FALLBACK_NODE]

    def understand(state: AnalysisState, config) -> AnalysisState:
        """Turn the question into a validated, runnable plan."""
        record = dataset_of(config)
        recent = (state.get("turns") or [])[-HISTORY_IN_PROMPT:]
        plan = language_agent.plan(record, state["question"], history=recent)
        source = "language model" if plan.source == "llm" else "keyword routing"
        detail = f"Interpreted the question as '{plan.intent}' using {source}."
        if recent and plan.source == "llm":
            detail += f" {len(recent)} earlier exchange(s) were in view."
        return {"plan": plan,
                "trace": [step("understand", language_agent.name, detail)]}

    def delegate(state: AnalysisState, config) -> AnalysisState:
        """Announce the hand-off. The plan already names its owning specialist."""
        plan = state["plan"]
        columns = ", ".join(plan.named_columns()) or "no specific columns"
        return {"trace": [step("delegate", language_agent.name,
                               f"Delegated to the {label(agents, plan.agent)} with {columns}.")]}

    def specialist(key: str, agent: Agent):
        """One computing node. Every figure in the result originates here, from pandas."""

        def node(state: AnalysisState, config) -> AnalysisState:
            try:
                result = agent.run(dataset_of(config), state["plan"])
            except AnalysisError as exc:
                # Not fatal: ``after_compute`` routes to ``recover`` instead of failing
                # the request outright.
                return {"error": str(exc),
                        "trace": [step("compute", agent.name,
                                       f"Could not complete that analysis: {exc}")]}
            return {"result": result, "error": "",
                    "trace": [step("compute", result.agent,
                                   f"Computed the {result.intent} result with pandas.")]}

        node.__name__ = f"{key}_node"
        return node

    def recover(state: AnalysisState, config) -> AnalysisState:
        """Answer with a dataset summary when the planned analysis could not run."""
        plan = state["plan"]
        if plan.intent == "summary":
            # The fallback itself failed — there is nothing safer to try. A 422 with the
            # specialist's own message is more useful than an empty summary.
            raise AnalysisError(state.get("error") or "The analysis could not be completed")
        plan.intent, plan.agent = "summary", FALLBACK_NODE
        result = insight.run(dataset_of(config), plan)
        result.caveats.append("The requested analysis could not be run on this dataset; "
                              "this is a general summary instead.")
        return {"result": result, "error": "",
                "trace": [step("recover", insight.name,
                               "Could not complete that analysis; answered with a dataset "
                               "summary instead.")]}

    def narrate(state: AnalysisState, config) -> AnalysisState:
        """Phrase the verified numbers, then commit the exchange to memory.

        This is the last node, so it is where a question becomes something the next
        question can refer back to. Only the shape of the exchange is kept — never the
        computed payload, which can be megabytes and is meaningless out of context.
        """
        result = insight.narrate(state["result"], state["question"], language_agent.client)
        detail = ("Explained the verified figures using the language model."
                  if result.narration_source == "llm" else "Used the deterministic explanation.")
        turn = Turn(question=state["question"], intent=result.intent,
                    agent=result.agent, answer=result.answer)
        return {"result": result, "turns": [turn],
                "trace": [step("narrate", insight.name, detail)]}

    nodes = {"understand": understand, "delegate": delegate}
    nodes.update({key: specialist(key, agent) for key, agent in agents.items()})
    nodes["recover"] = recover
    nodes["narrate"] = narrate
    return nodes
