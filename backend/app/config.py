import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

UPLOAD_DIR = BASE_DIR / "uploads"
GENERATED_DIR = BASE_DIR / "generated"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # LLM_PROVIDER picks one provider: "ollama" (official) or "cloudflare" (testing).
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")

    # Ollama — runs locally
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
    ollama_stream: bool = _bool("OLLAMA_STREAM", False)

    # Cloudflare Workers AI — hosted, used for testing
    cloudflare_account_id: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    cloudflare_api_token: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
    cloudflare_model: str = os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    cloudflare_timeout_seconds: float = float(os.getenv("CLOUDFLARE_TIMEOUT_SECONDS", "60"))
    cloudflare_temperature: float = float(os.getenv("CLOUDFLARE_TEMPERATURE", "0.1"))
    cloudflare_max_tokens: int = int(os.getenv("CLOUDFLARE_MAX_TOKENS", "1024"))


settings = Settings()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
