from app.config import settings
from app.llm.client import LLMClient

def test_ollama_configuration_comes_from_settings():
    client=LLMClient()
    assert client.config.ollama_base_url==settings.ollama_base_url
    assert client.config.ollama_model==settings.ollama_model
    assert client.config.ollama_timeout_seconds>0

