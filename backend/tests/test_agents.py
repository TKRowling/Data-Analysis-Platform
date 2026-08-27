"""The agent layer. The contract under test: an LLM may route and phrase, never calculate.

Requires the ``rich_record`` and ``scripted_client`` fixtures from conftest.py.
"""
import json

import pytest

from app.agents.base import AnalysisPlan, PlanColumns
from app.agents.language_agent import LanguageAgent
from app.agents.registry import AGENTS, INTENT_OWNERS, SKILLS, catalogue
from app.agents.validation import is_runnable, validate_plan
from app.core.exceptions import AnalysisError
from app.graphs.graph import AnalysisGraph, fresh_graph


# ------------------------------------------------------------------- registry
def test_every_skill_has_an_owner():
    for intent in SKILLS:
        assert INTENT_OWNERS[intent] in AGENTS


def test_catalogue_covers_the_four_specialists():
    assert {a["agent"] for a in catalogue()} == {
        "statistical_agent", "pattern_agent", "predictive_agent", "insight_agent"}


# ----------------------------------------------------------------- validation
def test_wrong_kind_column_is_rejected(rich_record):
    """A real column of the wrong kind must never reach pandas — this is the 500 guard."""
    plan = validate_plan(rich_record.frame, "ranking",
                         PlanColumns(group="product", metric="region"))
    assert plan.columns.metric is None
    assert any("region" in note for note in plan.rejected)
    assert not is_runnable(plan)


def test_unknown_column_is_rejected(rich_record):
    plan = validate_plan(rich_record.frame, "ranking",
                         PlanColumns(group="wizard", metric="unobtainium"))
    assert plan.named_columns() == []


def test_valid_plan_passes_untouched(rich_record):
    plan = validate_plan(rich_record.frame, "ranking",
                         PlanColumns(group="product", metric="revenue"), limit=3)
    assert (plan.columns.group, plan.columns.metric, plan.limit) == ("product", "revenue", 3)
    assert plan.rejected == []
    assert is_runnable(plan)


def test_unknown_intent_becomes_summary(rich_record):
    assert validate_plan(rich_record.frame, "teleport", PlanColumns()).intent == "summary"


# ------------------------------------------------------------------- planning
def test_keyword_routing_when_no_client(rich_record):
    plan = LanguageAgent(client=None).plan(rich_record, "top 3 products by revenue")
    assert (plan.source, plan.intent, plan.limit) == ("fallback", "ranking", 3)


def test_falls_back_when_llm_unreachable(rich_record, scripted_client):
    """An Ollama outage degrades to keyword routing rather than failing the request."""
    plan = LanguageAgent(client=scripted_client(fail=True)).plan(rich_record, "average revenue by region")
    assert plan.source == "fallback"
    assert plan.intent == "aggregation"
    assert plan.columns.metric == "revenue"


def test_llm_plan_is_used_when_valid(rich_record, scripted_client):
    reply = json.dumps({"intent": "ranking", "columns": {"group": "product", "metric": "revenue"},
                        "operation": "sum", "limit": 3, "chart": "bar"})
    plan = LanguageAgent(client=scripted_client(reply)).plan(rich_record, "best products")
    assert plan.source == "llm"
    assert (plan.intent, plan.columns.group, plan.columns.metric, plan.limit) == \
        ("ranking", "product", "revenue", 3)


def test_llm_wrong_kind_plan_falls_back(rich_record, scripted_client):
    bad = json.dumps({"intent": "ranking", "columns": {"group": "product", "metric": "region"}})
    plan = LanguageAgent(client=scripted_client(bad, bad)).plan(rich_record, "top products")
    assert plan.source == "fallback"


def test_garbage_json_retries_once_then_falls_back(rich_record, scripted_client):
    client = scripted_client("I cannot help with that.", "still not JSON")
    plan = LanguageAgent(client=client).plan(rich_record, "average revenue by region")
    assert plan.source == "fallback"
    assert len(client.calls) == 2


# ---------------------------------------------------- keyword routing accuracy
@pytest.mark.parametrize("question,intent", [
    ("Give me a summary of this dataset", "summary"),      # "sum" must not fire inside "summary"
    ("What is the total revenue by region", "aggregation"),
    ("What's the average revenue by region", "aggregation"),
    ("Top 5 products by revenue", "ranking"),
    ("Identify outliers in the price column", "outlier"),
    ("Show the correlation between units and revenue", "correlation"),
    ("Summary of product segments", "segmentation"),
    ("Predict revenue from units", "regression"),
])
def test_keyword_router_intents(rich_record, question, intent):
    assert LanguageAgent(client=None).plan(rich_record, question).intent == intent


def test_country_does_not_become_count(rich_record):
    """Substring matching would read 'count' out of 'country'."""
    frame = rich_record.frame
    frame["country"] = "KH"
    plan = LanguageAgent(client=None).plan(rich_record, "total revenue by country")
    assert plan.operation == "sum"


# ---------------------------------------------------------------- the pipeline
@pytest.mark.parametrize("question,intent,agent", [
    ("What are the top 3 products by revenue?", "ranking", "statistical_agent"),
    ("What is the average revenue by region?", "aggregation", "statistical_agent"),
    ("Identify outliers in the price column", "outlier", "statistical_agent"),
    ("Show the correlation between units and revenue", "correlation", "pattern_agent"),
    ("Give me a summary of product segments", "segmentation", "pattern_agent"),
    ("Predict revenue from units", "regression", "predictive_agent"),
    ("Give me an overview of this data", "summary", "insight_agent"),
])
def test_each_specialist_answers_and_verifies(rich_record, question, intent, agent):
    result = fresh_graph(client=None).run(rich_record, question)
    assert (result.intent, result.agent, result.verified) == (intent, agent, True)
    assert result.answer
    assert [s["stage"] for s in result.trace] == ["understand", "delegate", "compute", "narrate"]


def test_statistical_figures_match_pandas(rich_record):
    result = fresh_graph(client=None).run(rich_record, "What is the average revenue by region?")
    expected = rich_record.frame.groupby("region", dropna=False)["revenue"].mean()
    computed = {row["region"]: row["revenue"] for row in result.data["rows"]}
    for region, value in expected.items():
        assert computed[region] == pytest.approx(value)


def test_unrunnable_plan_recovers_instead_of_500(rich_record):
    """The conditional edge to `recover` keeps a bad plan from failing the request."""
    agent = LanguageAgent(client=None)
    agent.plan = lambda record, question: AnalysisPlan(
        intent="ranking", agent="statistical", columns=PlanColumns())
    result = AnalysisGraph(language_agent=agent).run(rich_record, "unanswerable ranking")
    assert result.intent == "summary"
    assert result.verified is True
    assert "recover" in [s["stage"] for s in result.trace]
    assert result.caveats


def test_specialist_rejects_a_plan_it_cannot_serve(rich_record):
    with pytest.raises(AnalysisError):
        AGENTS["statistical"].run(rich_record, AnalysisPlan(intent="outlier", agent="statistical"))


# ------------------------------------------------------------------ narration
def test_narration_rejects_invented_numbers(rich_record, scripted_client):
    from app.agents.base import AgentResult

    result = AgentResult("statistical_agent", "aggregation", "The mean of revenue is 250.0.",
                         {"metric": "revenue", "operation": "mean", "value": 250.0})
    narrated = AGENTS["insight"].narrate(result, "average revenue?",
                                         scripted_client("The mean revenue is 9999.99."))
    assert narrated.narration_source == "template"
    assert "9999.99" not in narrated.answer


def test_narration_accepts_grounded_text(rich_record, scripted_client):
    from app.agents.base import AgentResult

    result = AgentResult("statistical_agent", "aggregation", "The mean of revenue is 250.0.",
                         {"metric": "revenue", "operation": "mean", "value": 250.0})
    narrated = AGENTS["insight"].narrate(result, "average revenue?",
                                         scripted_client("Revenue averages 250.0 per order."))
    assert narrated.narration_source == "llm"


def test_narration_survives_llm_outage(rich_record, scripted_client):
    from app.agents.base import AgentResult

    result = AgentResult("statistical_agent", "aggregation", "Deterministic answer.", {"value": 1})
    narrated = AGENTS["insight"].narrate(result, "anything?", scripted_client(fail=True))
    assert narrated.answer == "Deterministic answer."
    assert narrated.narration_source == "template"


# --------------------------------------------------------- honesty guardrails
def test_auto_selected_features_are_flagged(rich_record):
    result = fresh_graph(client=None).run(rich_record, "predict revenue")
    assert any("automatically" in note for note in result.caveats)


def test_rescaled_copy_of_target_is_excluded(rich_record):
    rich_record.frame["revenue_usd"] = rich_record.frame["revenue"] * 1.09
    result = fresh_graph(client=None).run(rich_record, "predict revenue")
    assert "revenue_usd" not in result.data["features"]
    assert any("revenue_usd" in note for note in result.caveats)


def test_segmentation_survives_a_column_named_rows(rich_record):
    rich_record.frame["rows"] = 1
    result = fresh_graph(client=None).run(rich_record, "summary of region segments")
    assert result.intent == "segmentation"