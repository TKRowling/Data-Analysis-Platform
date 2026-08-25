"""AI analysis use case.

Thin delegation to the agent graph. The LLM boundary is created here so that a missing or
unreachable Ollama degrades to keyword routing instead of failing the request.
"""
from __future__ import annotations

import logging

from app.agents.column_resolver import resolve_column  # re-exported: used by callers and tests
from app.config import settings
from app.graphs.graph import AnalysisGraph
from app.llm.client import LLMClient

logger = logging.getLogger(__name__)

__all__ = ["analyze", "resolve_column", "llm_status"]

_graph: AnalysisGraph | None = None


def _client() -> LLMClient | None:
    """The Ollama client, or None when no provider is configured."""
    if settings.llm_provider.lower() in {"", "none", "off", "disabled"}:
        return None
    return LLMClient(settings)


def _analysis_graph() -> AnalysisGraph:
    global _graph
    if _graph is None:
        _graph = AnalysisGraph(client=_client())
    return _graph


def analyze(record, question: str) -> dict:
    result = _analysis_graph().run(record, question)
    return result.to_dict()


def llm_status() -> dict:
    """Whether agent narration and LLM routing are currently available."""
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
                       f"Cannot reach Ollama at {settings.ollama_base_url}. Questions are routed by keyword "
                       "and answers use deterministic explanations — every figure is still computed.")}
