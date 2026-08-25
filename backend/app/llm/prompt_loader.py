"""Load agent system prompts from app/llm/prompts/*.md."""
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt: {path}")
    return path.read_text(encoding="utf-8").strip()
