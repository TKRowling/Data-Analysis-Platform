"""Conversation memory for the analysis graph.

LangGraph persists one *thread* of state per conversation, so "memory" here is nothing
more exotic than: give a run a thread id, and the ``turns`` channel from last time is
still there when it starts.

Everything the checkpointer holds must be serializable, which is why the dataframe travels
in the run config (see ``state.dataset_of``) and the memory itself is a short list of small
dicts rather than the full results.

The default store is in-process: it disappears on restart, exactly like ``DatasetStore``,
whose dataframes it refers to. Durability is a one-line change — any ``BaseCheckpointSaver``
works here, so a SQLite or Postgres saver drops in without touching a node.
"""
from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

# Types the checkpointer is allowed to reconstruct. Without registering them LangGraph
# still deserializes, but warns that it will refuse outright in a later release.
ALLOWED_TYPES = [("app.agents.base", "AnalysisPlan"), ("app.agents.base", "AgentResult")]


def build_checkpointer() -> InMemorySaver:
    """The default in-process conversation store."""
    return InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_TYPES))


def thread(thread_id: str | None, record=None) -> dict:
    """A run config: which conversation to continue, and the dataset to run it against.

    A ``thread_id`` of None means "do not remember this". It produces a one-shot thread
    nothing will ever resume, which is how callers that want a stateless answer — and every
    caller that predates conversations — keep the behaviour they had.
    """
    return {"configurable": {"thread_id": thread_id or f"once-{uuid.uuid4()}",
                             "record": record}}
