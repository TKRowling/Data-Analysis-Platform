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


DETERMINISTIC_NOTE = ("Questions are routed by keyword and answers use deterministic "
                      "explanations — every figure is still computed.")

SUPPORTED_PROVIDERS = {"ollama", "cloudflare"}


def llm_status() -> dict:
    """Whether agent narration and LLM routing are currently available.

    Never includes the API token: this response is served to the browser.
    """
    client = _client()
    if client is None:
        return {"provider": settings.llm_provider, "available": False, "mode": "deterministic",
                "detail": f"No language model is configured. {DETERMINISTIC_NOTE}"}

    base = {"provider": client.provider, "model": client.model, "endpoint": client.endpoint,
            "available": False, "mode": "deterministic"}

    if client.provider not in SUPPORTED_PROVIDERS:
        return {**base, "detail": f"Unsupported LLM_PROVIDER {settings.llm_provider!r}. "
                                  f"Use 'ollama' or 'cloudflare'. {DETERMINISTIC_NOTE}"}

    missing = client.missing_config()
    if missing:
        return {**base, "detail": f"{client.provider} is selected but {missing} is not set. {DETERMINISTIC_NOTE}"}

    if client.health():
        return {**base, "available": True, "mode": "hybrid",
                "detail": f"The {client.provider} model {client.model} routes questions "
                          "and explains verified results."}

    return {**base, "detail": f"Cannot reach {client.provider} at {client.endpoint}. {DETERMINISTIC_NOTE}"}
