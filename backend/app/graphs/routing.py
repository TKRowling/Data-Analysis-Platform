"""Maps a validated plan to the specialist that owns it."""
from __future__ import annotations

from app.agents.base import INTENT_OWNERS, AnalysisPlan

AGENT_LABELS = {
    "statistical": "Statistical agent",
    "pattern": "Pattern recognition agent",
    "predictive": "Predictive agent",
    "insight": "Insight agent",
}


def select(plan: AnalysisPlan) -> str:
    """Agent family that should handle this plan."""
    return INTENT_OWNERS.get(plan.intent, plan.agent if plan.agent in AGENT_LABELS else "insight")


def label(agent: str) -> str:
    return AGENT_LABELS.get(agent, agent)
