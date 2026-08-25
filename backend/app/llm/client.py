import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings, settings

# After a connection failure, stop retrying for this long. Without it every question pays
# two connection timeouts when Ollama is not running.
COOLDOWN_SECONDS = 30.0


class LLMClient:
    """LLM boundary configured entirely through environment variables."""

    def __init__(self, config: Settings = settings):
        self.config = config
        self._unavailable_until = 0.0

    @property
    def cooling_down(self) -> bool:
        return time.monotonic() < self._unavailable_until

    def _trip(self) -> None:
        self._unavailable_until = time.monotonic() + COOLDOWN_SECONDS

    def _reset(self) -> None:
        self._unavailable_until = 0.0

    def complete(self, prompt: str, system: str | None = None) -> str:
        if self.config.llm_provider != "ollama":
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {self.config.llm_provider}")
        if self.cooling_down:
            raise RuntimeError(f"Ollama was unreachable moments ago; retrying in {COOLDOWN_SECONDS:.0f}s")
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
        request = Request(
            f"{self.config.ollama_base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.ollama_timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Ollama returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            self._trip()
            raise RuntimeError(f"Could not connect to Ollama at {self.config.ollama_base_url}") from exc
        self._reset()
        if not result.get("response"):
            raise RuntimeError("Ollama returned an empty response")
        return str(result["response"])

    def health(self) -> bool:
        request = Request(f"{self.config.ollama_base_url}/api/tags", method="GET")
        try:
            with urlopen(request, timeout=min(self.config.ollama_timeout_seconds, 5)) as response:
                healthy = response.status == 200
        except (HTTPError, URLError, TimeoutError, OSError):
            self._trip()
            return False
        if healthy:
            self._reset()
        return healthy
