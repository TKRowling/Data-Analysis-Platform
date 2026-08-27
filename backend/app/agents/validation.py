"""Validate a proposed plan against the real dataframe.

Checking that a column *exists* is not enough. A planner model that returns
``{"intent": "ranking", "group": "product", "metric": "region"}`` names two real columns,
but summing a text column raises a TypeError deep inside pandas, which surfaces as a 500
rather than the 422 the API promises.

Every slot is therefore checked against the kind the skill declares it needs. A slot
holding the wrong kind is emptied and recorded in ``plan.rejected``; the caller decides
whether to fall back. Nothing here raises.
"""
from __future__ import annotations

from app.agents.base import AnalysisPlan, PlanColumns, Skill
from app.agents.registry import VALID_CHARTS, VALID_OPERATIONS, owner, skill_for
from app.utils.dataframe_utils import column_kind

SINGLE_SLOTS = ("group", "metric", "x", "y", "target")
NUMERIC_KINDS = {"numeric"}
CATEGORICAL_KINDS = {"categorical", "boolean", "datetime"}
TEMPORAL_KINDS = {"datetime"}


def _accepts(skill: Skill | None, slot: str) -> set[str] | None:
    """Kinds allowed in this slot, or None when the skill has no opinion."""
    if skill is None:
        return None
    if slot in skill.numeric:
        return NUMERIC_KINDS
    if slot in skill.categorical:
        return CATEGORICAL_KINDS
    if slot in skill.temporal:
        return TEMPORAL_KINDS
    return None


def validate_plan(frame, intent: str, columns: PlanColumns, *, operation: str = "sum",
                  limit: int = 5, chart: str | None = None,
                  source: str = "llm") -> AnalysisPlan:
    """Build a plan that is safe to execute. Unusable slots are emptied, not repaired."""
    from app.agents.registry import VALID_INTENTS

    if intent not in VALID_INTENTS:
        intent = "summary"
    skill = skill_for(intent)
    available = set(frame.columns)
    picked = columns.model_dump()
    rejected: list[str] = []

    for slot in SINGLE_SLOTS:
        name = picked.get(slot)
        if name is None:
            continue
        if name not in available:
            picked[slot] = None
            rejected.append(f"{slot}={name} (no such column)")
            continue
        allowed = _accepts(skill, slot)
        kind = column_kind(frame[name])
        if allowed is not None and kind not in allowed:
            picked[slot] = None
            rejected.append(f"{slot}={name} (is {kind}, needs {'/'.join(sorted(allowed))})")

    features_allowed = _accepts(skill, "features") or set()
    kept_features = []
    for name in picked.get("features") or []:
        if name not in available:
            rejected.append(f"features={name} (no such column)")
            continue
        if features_allowed and column_kind(frame[name]) not in features_allowed:
            rejected.append(f"features={name} (wrong kind)")
            continue
        kept_features.append(name)
    picked["features"] = kept_features

    # A group slot that landed on the target of a prediction is not a grouping.
    if picked.get("group") and picked["group"] == picked.get("metric"):
        picked["group"] = None

    return AnalysisPlan(
        intent=intent,
        agent=owner(intent),
        columns=PlanColumns(**picked),
        operation=operation if operation in VALID_OPERATIONS else "sum",
        limit=max(1, min(int(limit or 5), 50)),
        chart=chart if chart in VALID_CHARTS else (skill.chart if skill else None),
        source=source,  # type: ignore[arg-type]
        rejected=rejected,
    )


def is_runnable(plan: AnalysisPlan) -> bool:
    """Whether every slot the skill marks required is filled."""
    skill = skill_for(plan.intent)
    if skill is None:
        return plan.intent == "summary"
    filled = plan.columns.model_dump()
    for slot in skill.required:
        value = filled.get(slot)
        if not value:
            return False
    return True