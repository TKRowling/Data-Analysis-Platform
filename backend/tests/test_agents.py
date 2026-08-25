"""The agent layer. The contract under test: an LLM may route and phrase, never calculate."""
import json

import pytest

from app.agents.base import AnalysisPlan, PlanColumns
from app.agents.orchestrator_agent import OrchestratorAgent
from app.core.exceptions import AnalysisError
from app.graphs.graph import AnalysisGraph


def test_orchestrator_routes_correlation():
    assert OrchestratorAgent().route("correlation between age and income") == "pattern"


def test_keyword_routing_when_no_client(rich_record):
    """With no LLM configured the platform still answers, using the deterministic router."""
    plan = OrchestratorAgent(client=None).plan(rich_record, "top 3 products by revenue")
    assert plan.source == "fallback"
    assert plan.intent == "ranking"
    assert plan.limit == 3


def test_falls_back_when_llm_unreachable(rich_record, scripted_client):
    """An Ollama outage must degrade to keyword routing, not fail the request."""
    client = scripted_client(fail=True)
    plan = OrchestratorAgent(client=client).plan(rich_record, "average revenue by region")
    assert plan.source == "fallback"
    assert plan.intent == "aggregation"
    assert plan.columns.metric == "revenue"


def test_llm_plan_is_used_when_valid(rich_record, scripted_client):
    reply = json.dumps({"intent": "ranking", "columns": {"group": "product", "metric": "revenue"},
                        "operation": "sum", "limit": 3, "chart": "bar"})
    plan = OrchestratorAgent(client=scripted_client(reply)).plan(rich_record, "best products")
    assert plan.source == "llm"
    assert (plan.intent, plan.columns.group, plan.columns.metric, plan.limit) == ("ranking", "product", "revenue", 3)


def test_llm_hallucinated_column_is_rejected(rich_record, scripted_client):
    """A column the model invented must never reach pandas."""
    reply = json.dumps({"intent": "ranking", "columns": {"group": "made_up_column", "metric": "also_fake"},
                        "operation": "sum", "limit": 5})
    plan = OrchestratorAgent(client=scripted_client(reply)).plan(rich_record, "top products by revenue")
    for column in plan.named_columns():
        assert column in rich_record.frame.columns


def test_llm_unknown_intent_becomes_summary(rich_record, scripted_client):
    reply = json.dumps({"intent": "teleport", "columns": {}})
    plan = OrchestratorAgent(client=scripted_client(reply)).plan(rich_record, "do something odd")
    assert plan.intent == "summary"


def test_garbage_json_falls_back(rich_record, scripted_client):
    client = scripted_client("I cannot help with that.", "still not JSON")
    plan = OrchestratorAgent(client=client).plan(rich_record, "average revenue by region")
    assert plan.source == "fallback"
    assert len(client.calls) == 2  # one attempt plus one corrective retry


@pytest.mark.parametrize("question,intent,agent", [
    ("What are the top 3 products by revenue?", "ranking", "statistical_agent"),
    ("What is the average revenue by region?", "aggregation", "statistical_agent"),
    ("Identify outliers in the price column", "outlier", "statistical_agent"),
    ("Show the correlation between units and revenue", "correlation", "pattern_agent"),
    ("Give me a summary of product segments", "segmentation", "pattern_agent"),
    ("Predict revenue from units", "regression", "predictive_agent"),
    ("Tell me about this data", "summary", "insight_agent"),
])
def test_each_specialist_answers_and_verifies(rich_record, question, intent, agent):
    result = AnalysisGraph(client=None).run(rich_record, question)
    assert result.intent == intent
    assert result.agent == agent
    assert result.verified is True
    assert result.answer
    assert len(result.trace) == 4


def test_statistical_figures_match_pandas(rich_record):
    result = AnalysisGraph(client=None).run(rich_record, "What is the average revenue by region?")
    expected = rich_record.frame.groupby("region", dropna=False)["revenue"].mean()
    computed = {row["region"]: row["revenue"] for row in result.data["rows"]}
    for region, value in expected.items():
        assert computed[region] == pytest.approx(value)


def test_correlation_matches_pandas(rich_record):
    result = AnalysisGraph(client=None).run(rich_record, "correlation between units and revenue")
    expected = rich_record.frame["units"].corr(rich_record.frame["revenue"])
    assert result.data["correlation"] == pytest.approx(expected, abs=1e-4)


def test_specialist_error_degrades_to_summary(rich_record):
    """A plan the specialist cannot run answers with an overview rather than a 500."""
    orchestrator = OrchestratorAgent(client=None)
    graph = AnalysisGraph(orchestrator=orchestrator)
    orchestrator.plan = lambda record, question: AnalysisPlan(
        intent="ranking", agent="statistical", columns=PlanColumns())
    result = graph.run(rich_record, "unanswerable ranking")
    assert result.intent == "summary"
    assert result.verified is True


def test_insight_narration_rejects_invented_numbers(rich_record, scripted_client):
    """If the model states a figure that is not in the verified result, keep the template."""
    from app.agents.insight_agent import InsightAgent
    from app.agents.base import AgentResult

    result = AgentResult("statistical_agent", "aggregation", "The mean of revenue is 250.00.",
                         {"metric": "revenue", "operation": "mean", "value": 250.0})
    narrated = InsightAgent().narrate(result, "average revenue?", scripted_client("The mean revenue is 9999.99."))
    assert narrated.narration_source == "template"
    assert "9999.99" not in narrated.answer


def test_insight_narration_accepts_grounded_text(rich_record, scripted_client):
    from app.agents.insight_agent import InsightAgent
    from app.agents.base import AgentResult

    result = AgentResult("statistical_agent", "aggregation", "The mean of revenue is 250.0.",
                         {"metric": "revenue", "operation": "mean", "value": 250.0})
    narrated = InsightAgent().narrate(result, "average revenue?", scripted_client("Revenue averages 250.0 per order."))
    assert narrated.narration_source == "llm"
    assert "250.0" in narrated.answer


def test_narration_survives_llm_outage(rich_record, scripted_client):
    from app.agents.insight_agent import InsightAgent
    from app.agents.base import AgentResult

    result = AgentResult("statistical_agent", "aggregation", "Deterministic answer.", {"value": 1})
    narrated = InsightAgent().narrate(result, "anything?", scripted_client(fail=True))
    assert narrated.answer == "Deterministic answer."
    assert narrated.narration_source == "template"


def test_outlier_without_column_is_a_clean_error(rich_record):
    from app.agents.statistical_agent import StatisticalAgent
    with pytest.raises(AnalysisError):
        StatisticalAgent().run(rich_record, AnalysisPlan(intent="outlier", agent="statistical"))
