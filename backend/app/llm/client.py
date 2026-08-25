"""LLM boundary. Supports two providers, chosen by the LLM_PROVIDER environment variable:

    ollama     - runs on your own machine (the official service)
    cloudflare - Cloudflare Workers AI, hosted (used for testing)

Only one is active at a time. If it is unreachable, complete() raises and the agent layer
falls back to keyword routing, so the platform keeps working either way.
"""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings, settings

# After a connection failure, stop retrying for this long. Without it every question pays
# a fresh connection timeout while the provider is down.
COOLDOWN_SECONDS = 30.0

CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"


def _request_json(url, payload=None, headers=None, timeout=30):
    """Send a JSON request and return the decoded reply.

    Raises ConnectionError if the server could not be reached, RuntimeError if it
    answered with an error status.
    """
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    all_headers = {"Content-Type": "application/json"}
    if headers:
        all_headers.update(headers)
    request = Request(url, data=data, headers=all_headers, method="POST" if data else "GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ConnectionError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("the reply was not valid JSON") from exc


class LLMClient:
    """LLM boundary configured entirely through environment variables."""

    def __init__(self, config: Settings = settings):
        self.config = config
        self._unavailable_until = 0.0

    @property
    def provider(self) -> str:
        return self.config.llm_provider.strip().lower()

    @property
    def model(self) -> str:
        """The model in use for the active provider."""
        if self.provider == "cloudflare":
            return self.config.cloudflare_model
        return self.config.ollama_model

    @property
    def endpoint(self) -> str:
        """Where requests go. Safe to show in the UI - never contains the API token."""
        if self.provider == "cloudflare":
            return f"{CLOUDFLARE_API}/accounts/{self.config.cloudflare_account_id or '<account-id>'}/ai/run"
        return self.config.ollama_base_url

    @property
    def cooling_down(self) -> bool:
        return time.monotonic() < self._unavailable_until

    def _trip(self) -> None:
        self._unavailable_until = time.monotonic() + COOLDOWN_SECONDS

    def _reset(self) -> None:
        self._unavailable_until = 0.0

    # ── public API ──────────────────────────────────────────────────────

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Ask the active provider for a completion. Raises if it cannot answer.

        Configuration problems are reported before the cooldown, because waiting will
        never fix a missing setting and the real cause is more useful to see.
        """
        if self.provider not in ("ollama", "cloudflare"):
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {self.config.llm_provider!r}. "
                               f"Use 'ollama' or 'cloudflare'.")
        missing = self.missing_config()
        if missing:
            raise RuntimeError(f"{self.provider} is selected but {missing} is not set")
        if self.cooling_down:
            raise RuntimeError(
                f"{self.provider} was unreachable moments ago; retrying in {COOLDOWN_SECONDS:.0f}s")

        if self.provider == "ollama":
            text = self._ollama_complete(prompt, system)
        else:
            text = self._cloudflare_complete(prompt, system)
        self._reset()
        return text

    def health(self) -> bool:
        """Whether the active provider is reachable right now. Never raises."""
        # An unsupported provider or a blank credential is a configuration problem, not an
        # outage, so it does not trip the breaker.
        if self.provider not in ("ollama", "cloudflare") or self.missing_config():
            return False
        try:
            healthy = self._ollama_health() if self.provider == "ollama" else self._cloudflare_health()
        except (ConnectionError, RuntimeError):
            self._trip()
            return False
        if healthy:
            self._reset()
        else:
            self._trip()
        return healthy

    def missing_config(self) -> str:
        """Which required setting is blank, or '' when the provider is configured."""
        if self.provider == "cloudflare":
            if not self.config.cloudflare_account_id:
                return "CLOUDFLARE_ACCOUNT_ID"
            if not self.config.cloudflare_api_token:
                return "CLOUDFLARE_API_TOKEN"
        return ""

    # ── Ollama ──────────────────────────────────────────────────────────

    def _ollama_complete(self, prompt: str, system: str | None) -> str:
        payload = {
            "model": self.config.ollama_model,
            "prompt": prompt,
            "system": system or "",
            "stream": self.config.ollama_stream,
            "keep_alive": self.config.ollama_keep_alive,
            "options": {
                "temperature": self.config.ollama_temperature,
                "num_ctx": self.config.ollama_num_ctx,
            },
        }
        try:
            result = _request_json(f"{self.config.ollama_base_url}/api/generate", payload,
                                   timeout=self.config.ollama_timeout_seconds)
        except ConnectionError as exc:
            self._trip()
            raise RuntimeError(f"Could not connect to Ollama at {self.config.ollama_base_url}") from exc
        except RuntimeError as exc:
            raise RuntimeError(f"Ollama returned an error: {exc}") from exc
        if not result.get("response"):
            raise RuntimeError("Ollama returned an empty response")
        return str(result["response"])

    def _ollama_health(self) -> bool:
        timeout = min(self.config.ollama_timeout_seconds, 5)
        _request_json(f"{self.config.ollama_base_url}/api/tags", timeout=timeout)
        return True

    # ── Cloudflare Workers AI ───────────────────────────────────────────

    def _cloudflare_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.cloudflare_api_token}"}

    def _cloudflare_complete(self, prompt: str, system: str | None) -> str:
        missing = self.missing_config()
        if missing:
            raise RuntimeError(f"Cloudflare is selected but {missing} is not set")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "messages": messages,
            "temperature": self.config.cloudflare_temperature,
            "max_tokens": self.config.cloudflare_max_tokens,
        }
        url = f"{CLOUDFLARE_API}/accounts/{self.config.cloudflare_account_id}/ai/run/{self.config.cloudflare_model}"
        try:
            body = _request_json(url, payload, headers=self._cloudflare_headers(),
                                 timeout=self.config.cloudflare_timeout_seconds)
        except ConnectionError as exc:
            self._trip()
            raise RuntimeError("Could not connect to Cloudflare Workers AI") from exc
        except RuntimeError as exc:
            raise RuntimeError(f"Cloudflare returned an error: {exc}") from exc

        # Cloudflare can report failure with a 200 status, so check `success` as well.
        if not body.get("success", False):
            raise RuntimeError(f"Cloudflare rejected the request: {_cloudflare_error(body)}")
        text = (body.get("result") or {}).get("response")
        if not text:
            raise RuntimeError("Cloudflare returned an empty response")
        return str(text)

    def _cloudflare_health(self) -> bool:
        if self.missing_config():
            return False
        url = f"{CLOUDFLARE_API}/accounts/{self.config.cloudflare_account_id}/ai/models/search?per_page=1"
        body = _request_json(url, headers=self._cloudflare_headers(),
                             timeout=min(self.config.cloudflare_timeout_seconds, 5))
        return bool(body.get("success", False))


def _cloudflare_error(body: dict) -> str:
    """Pull a readable message out of Cloudflare's error envelope."""
    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict) and first.get("message"):
            return str(first["message"])
    return "no reason given"
