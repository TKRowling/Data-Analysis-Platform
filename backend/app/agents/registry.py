"""The agent roster.

Intent ownership is *derived* from the skills each agent declares, so there is no separate
table to keep in sync. Add a Skill to an agent and routing, validation, and the planner
prompt all pick it up.
"""
from __future__ import annotations

from app.agents.base import Agent, Skill
from app.agents.insight_agent import InsightAgent
from app.agents.pattern_agent import PatternAgent
from app.agents.predictive_agent import PredictiveAgent
from app.agents.statistical_agent import StatisticalAgent


def build_agents() -> dict[str, Agent]:
    """One instance of each specialist, keyed by short name."""
    return {
        "statistical": StatisticalAgent(),
        "pattern": PatternAgent(),
        "predictive": PredictiveAgent(),
        "insight": InsightAgent(),
    }


AGENTS: dict[str, Agent] = build_agents()

# intent -> short agent name
INTENT_OWNERS: dict[str, str] = {
    skill.intent: key for key, agent in AGENTS.items() for skill in agent.skills
}
# "relationship" is a phrasing of correlation; keep it routable without a duplicate Skill.
INTENT_OWNERS.setdefault("relationship", "pattern")

# intent -> Skill
SKILLS: dict[str, Skill] = {
    skill.intent: skill for agent in AGENTS.values() for skill in agent.skills
}

VALID_INTENTS = frozenset(INTENT_OWNERS)
VALID_OPERATIONS = frozenset({"sum", "mean", "median", "min", "max", "count"})
VALID_CHARTS = frozenset({"bar", "line", "scatter", "histogram", "box", "pie", "heatmap"})


def owner(intent: str) -> str:
    return INTENT_OWNERS.get(intent, "insight")


def skill_for(intent: str) -> Skill | None:
    return SKILLS.get(intent)


def catalogue() -> list[dict]:
    """Every agent and its skills — for the planner prompt and the UI's agent panel."""
    return [agent.describe() for agent in AGENTS.values()]


def skill_menu() -> list[dict]:
    """Flat intent list handed to the planner model."""
    return [{**skill.describe(), "agent": INTENT_OWNERS[skill.intent]} for skill in SKILLS.values()]