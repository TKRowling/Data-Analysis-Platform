"""AI analysis use case.

Thin delegation to the agent graph. The LLM boundary is created here so that a missing or
unreachable Ollama degrades to keyword routing instead of failing the request.
"""
from __future__ import annotations

import logging

from app.agents.column_resolver import resolve_column  # re-exported for callers and tests
from app.agents.registry import catalogue
from app.config import settings
from app.graphs.graph import AnalysisGraph
from app.llm.client import LLMClient

logger = logging.getLogger(__name__)

__all__ = ["analyze", "resolve_column", "llm_status", "agents", "memory", "forget"]

_graph: AnalysisGraph | None = None


def _client() -> LLMClient | None:
    """The Ollama client, or None when no provider is configured."""
    if settings.llm_provider.lower() in {"", "none", "off", "disabled"}:
        return None
    return LLMClient(settings)


def _analysis_graph() -> AnalysisGraph:
    """Compiled once — LangGraph compilation is not free and the topology is static."""
    global _graph
    if _graph is None:
        _graph = AnalysisGraph(client=_client())
    return _graph


def _thread_for(record, conversation_id: str | None) -> str:
    """Which conversation this question belongs to.

    Defaults to the dataset: ask two questions about the same data and the second one
    can refer back to the first, with no client change needed. Pass an explicit
    conversation_id to scope memory more narrowly — which is what a multi-user
    deployment must do, since a per-dataset thread is shared by every caller.
    """
    return conversation_id or record.id


def analyze(record, question: str, conversation_id: str | None = None) -> dict:
    thread_id = _thread_for(record, conversation_id)
    return _analysis_graph().run(record, question, thread_id=thread_id).to_dict()


def memory(record, conversation_id: str | None = None) -> list[dict]:
    """The exchanges this conversation still remembers, oldest first."""
    return _analysis_graph().history(_thread_for(record, conversation_id))


def forget(record, conversation_id: str | None = None) -> None:
    """Drop the conversation. The next question starts with no context."""
    _analysis_graph().forget(_thread_for(record, conversation_id))


def agents() -> list[dict]:
    """Every agent and the skills it declares — powers the UI's agent panel."""
    return catalogue()


def llm_status() -> dict:
    """Whether LLM routing and narration are available. Analysis works either way."""
    client = _client()
    if client is None:
        return {"provider": settings.llm_provider, "available": False, "mode": "deterministic",
                "detail": "No language model is configured. Questions are routed by keyword."}
    available = client.health()
    return {"provider": settings.llm_provider, "model": settings.ollama_model,
            "base_url": settings.ollama_base_url, "available": available,
            "mode": "hybrid" if available else "deterministic",
            "detail": ("The language model routes questions and explains verified results."
                       if available else
                       f"Cannot reach Ollama at {settings.ollama_base_url}. Questions are routed "
                       "by keyword and answers use deterministic explanations — every figure is "
                       "still computed.")}