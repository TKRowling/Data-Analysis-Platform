"""The LLM boundary: two providers, selected by LLM_PROVIDER.

Settings is a frozen dataclass, so each test builds its own instead of mutating the
environment. That keeps tests isolated from the developer's real .env file.
"""
import pytest

from app.config import Settings, settings
from app.llm import client as client_module
from app.llm.client import LLMClient


def make_client(**overrides) -> LLMClient:
    return LLMClient(Settings(**overrides))


# ── Ollama ──────────────────────────────────────────────────────────────

def test_ollama_configuration_comes_from_settings():
    client = LLMClient()
    assert client.config.ollama_base_url == settings.ollama_base_url
    assert client.config.ollama_model == settings.ollama_model
    assert client.config.ollama_timeout_seconds > 0


def test_ollama_is_the_default_provider():
    client = make_client()
    assert client.provider == "ollama"
    assert client.model == settings.ollama_model
    assert client.endpoint == settings.ollama_base_url


def test_ollama_reads_the_response_field(monkeypatch):
    monkeypatch.setattr(client_module, "_request_json", lambda *a, **k: {"response": "hello"})
    assert make_client(llm_provider="ollama").complete("hi") == "hello"


def test_ollama_empty_response_is_an_error(monkeypatch):
    monkeypatch.setattr(client_module, "_request_json", lambda *a, **k: {"response": ""})
    with pytest.raises(RuntimeError, match="empty response"):
        make_client(llm_provider="ollama").complete("hi")


# ── Cloudflare ──────────────────────────────────────────────────────────

def cloudflare_client(**overrides) -> LLMClient:
    return make_client(llm_provider="cloudflare", cloudflare_account_id="acct-123",
                       cloudflare_api_token="token-abc", **overrides)


def test_cloudflare_selected_by_provider_name():
    client = cloudflare_client()
    assert client.provider == "cloudflare"
    assert client.model == "@cf/meta/llama-3.1-8b-instruct"
    assert "acct-123" in client.endpoint


def test_cloudflare_reads_the_nested_response(monkeypatch):
    monkeypatch.setattr(client_module, "_request_json",
                        lambda *a, **k: {"success": True, "result": {"response": "hi there"}})
    assert cloudflare_client().complete("question") == "hi there"


def test_cloudflare_failure_with_200_status_is_an_error(monkeypatch):
    """Cloudflare reports some failures with success:false and an HTTP 200."""
    monkeypatch.setattr(client_module, "_request_json",
                        lambda *a, **k: {"success": False, "errors": [{"message": "Model not found"}]})
    with pytest.raises(RuntimeError, match="Model not found"):
        cloudflare_client().complete("question")


def test_cloudflare_empty_response_is_an_error(monkeypatch):
    monkeypatch.setattr(client_module, "_request_json",
                        lambda *a, **k: {"success": True, "result": {"response": ""}})
    with pytest.raises(RuntimeError, match="empty response"):
        cloudflare_client().complete("question")


def test_cloudflare_sends_the_system_prompt_as_a_message(monkeypatch):
    captured = {}

    def fake_request(url, payload=None, headers=None, timeout=30):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"success": True, "result": {"response": "ok"}}

    monkeypatch.setattr(client_module, "_request_json", fake_request)
    cloudflare_client().complete("the question", system="the system prompt")

    roles = [m["role"] for m in captured["payload"]["messages"]]
    assert roles == ["system", "user"]
    assert captured["payload"]["messages"][1]["content"] == "the question"
    assert captured["headers"]["Authorization"] == "Bearer token-abc"
    assert "acct-123" in captured["url"]


@pytest.mark.parametrize("overrides,missing", [
    ({"cloudflare_account_id": "", "cloudflare_api_token": "t"}, "CLOUDFLARE_ACCOUNT_ID"),
    ({"cloudflare_account_id": "a", "cloudflare_api_token": ""}, "CLOUDFLARE_API_TOKEN"),
])
def test_cloudflare_reports_missing_credentials(overrides, missing):
    client = make_client(llm_provider="cloudflare", **overrides)
    assert client.missing_config() == missing
    assert client.health() is False
    with pytest.raises(RuntimeError, match=missing):
        client.complete("question")


# ── Provider selection ──────────────────────────────────────────────────

def test_unsupported_provider_names_the_bad_value():
    client = make_client(llm_provider="banana")
    with pytest.raises(RuntimeError, match="banana"):
        client.complete("question")
    assert client.health() is False


def test_provider_name_is_case_and_space_tolerant():
    assert make_client(llm_provider="  Cloudflare ").provider == "cloudflare"


def test_connection_failure_trips_the_breaker(monkeypatch):
    """A dead provider is not retried on every request."""
    def refuse(*args, **kwargs):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(client_module, "_request_json", refuse)
    client = make_client(llm_provider="ollama")
    with pytest.raises(RuntimeError, match="Could not connect"):
        client.complete("question")
    assert client.cooling_down is True
    with pytest.raises(RuntimeError, match="moments ago"):
        client.complete("question")


# ── Status endpoint ─────────────────────────────────────────────────────

def test_status_never_leaks_the_api_token(monkeypatch):
    import json
    from app.services import ai_service

    secret = "super-secret-token-value"
    monkeypatch.setattr(ai_service, "settings",
                        Settings(llm_provider="cloudflare", cloudflare_account_id="acct",
                                 cloudflare_api_token=secret))
    monkeypatch.setattr(LLMClient, "health", lambda self: True)
    body = json.dumps(ai_service.llm_status())
    assert secret not in body
    assert "cloudflare" in body


def test_status_reports_missing_credentials(monkeypatch):
    from app.services import ai_service
    monkeypatch.setattr(ai_service, "settings", Settings(llm_provider="cloudflare"))
    status = ai_service.llm_status()
    assert status["available"] is False
    assert status["mode"] == "deterministic"
    assert "CLOUDFLARE_ACCOUNT_ID" in status["detail"]


def test_status_reports_an_unsupported_provider(monkeypatch):
    from app.services import ai_service
    monkeypatch.setattr(ai_service, "settings", Settings(llm_provider="banana"))
    status = ai_service.llm_status()
    assert status["available"] is False
    assert "banana" in status["detail"]
