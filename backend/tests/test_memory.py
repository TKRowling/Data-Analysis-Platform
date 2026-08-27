"""Conversation memory — the LangGraph checkpointer behind AI analysis.

Requires the ``rich_record`` and ``scripted_client`` fixtures from conftest.py.
"""
import json

from app.agents.language_agent import LanguageAgent
from app.graphs.graph import AnalysisGraph, fresh_graph
from app.graphs.memory import thread
from app.graphs.state import MEMORY_TURNS


# ------------------------------------------------------------------ storing

def test_a_thread_remembers_its_questions(rich_record):
    graph = fresh_graph(client=None)
    graph.run(rich_record, "top 5 products by revenue", thread_id="c1")
    graph.run(rich_record, "average revenue by region", thread_id="c1")

    remembered = graph.history("c1")
    assert [turn["question"] for turn in remembered] == [
        "top 5 products by revenue", "average revenue by region"]
    assert remembered[0]["intent"] == "ranking"
    assert remembered[0]["agent"] == "statistical_agent"
    assert remembered[0]["answer"]


def test_threads_do_not_share_memory(rich_record):
    graph = fresh_graph(client=None)
    graph.run(rich_record, "top 5 products by revenue", thread_id="mine")
    graph.run(rich_record, "summary", thread_id="yours")

    assert [t["question"] for t in graph.history("mine")] == ["top 5 products by revenue"]
    assert [t["question"] for t in graph.history("yours")] == ["summary"]


def test_without_a_thread_id_nothing_is_remembered(rich_record):
    """The pre-conversation contract: a bare run() keeps no state anywhere."""
    graph = fresh_graph(client=None)
    graph.run(rich_record, "summary")
    graph.run(rich_record, "summary")

    threads = {c.config["configurable"]["thread_id"] for c in graph.checkpointer.list(None)}
    assert len(threads) == 2, "each anonymous run must get its own throwaway thread"
    assert all(t.startswith("once-") for t in threads)


def test_memory_is_bounded(rich_record):
    graph = fresh_graph(client=None)
    for index in range(MEMORY_TURNS + 3):
        graph.run(rich_record, f"summary {index}", thread_id="long")

    remembered = graph.history("long")
    assert len(remembered) == MEMORY_TURNS
    # The oldest fell off the front; the newest is still there.
    assert remembered[-1]["question"] == f"summary {MEMORY_TURNS + 2}"
    assert all("summary 0" != turn["question"] for turn in remembered)


def test_forget_clears_the_conversation(rich_record):
    graph = fresh_graph(client=None)
    graph.run(rich_record, "summary", thread_id="temp")
    assert graph.history("temp")

    graph.forget("temp")
    assert graph.history("temp") == []


def test_history_of_an_unknown_thread_is_empty(rich_record):
    assert fresh_graph(client=None).history("never-asked-anything") == []


# ------------------------------------------------------------------ isolation

def test_trace_does_not_accumulate_across_questions(rich_record):
    """Memory persists; the per-question hand-off trail does not."""
    graph = fresh_graph(client=None)
    first = graph.run(rich_record, "top 5 products by revenue", thread_id="c2")
    second = graph.run(rich_record, "average revenue by region", thread_id="c2")

    assert len(second.trace) == len(first.trace)
    assert [s["step"] for s in second.trace] == list(range(1, len(second.trace) + 1))
    assert "top 5 products" not in json.dumps(second.trace)


def test_the_dataframe_never_reaches_the_checkpointer(rich_record):
    """The reason ``record`` lives in the config: state is serialized after every node."""
    graph = fresh_graph(client=None)
    graph.run(rich_record, "summary", thread_id="c3")

    snapshot = graph.compiled.get_state(thread("c3"))
    assert "record" not in snapshot.values
    # And every checkpoint round-trips through the serializer without the frame in it.
    assert list(graph.checkpointer.list(thread("c3")))


# ------------------------------------------------------------------ planning

def test_planner_sees_earlier_exchanges(rich_record, scripted_client):
    reply = json.dumps({"intent": "ranking", "columns": {"group": "product", "metric": "revenue"},
                        "operation": "sum", "limit": 5})
    client = scripted_client(reply, reply)
    graph = AnalysisGraph(language_agent=LanguageAgent(client=client))

    graph.run(rich_record, "top products by revenue", thread_id="c4")
    graph.run(rich_record, "what about the top 10?", thread_id="c4")

    assert "Earlier in this conversation" not in client.calls[0], "first question has no history"
    assert "top products by revenue" in client.calls[1], "the follow-up must see the first"


def test_keyword_fallback_ignores_history(rich_record):
    """A question routed without a model is planned identically, follow-up or not."""
    graph = fresh_graph(client=None)
    graph.run(rich_record, "top 5 products by revenue", thread_id="c5")
    followup = graph.run(rich_record, "average revenue by region", thread_id="c5")
    standalone = fresh_graph(client=None).run(rich_record, "average revenue by region")

    assert followup.intent == standalone.intent == "aggregation"
    assert followup.data["rows"] == standalone.data["rows"]
