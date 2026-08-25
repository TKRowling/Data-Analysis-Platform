import pytest
from pydantic import BaseModel

from app.llm.structured_output import StructuredOutputError, extract_json, parse_structured


class Plan(BaseModel):
    intent: str
    limit: int = 5


def test_extracts_plain_json():
    assert extract_json('{"intent": "ranking"}') == {"intent": "ranking"}


def test_extracts_from_code_fence():
    raw = 'Here you go:\n```json\n{"intent": "ranking", "limit": 3}\n```\nHope that helps.'
    assert extract_json(raw) == {"intent": "ranking", "limit": 3}


def test_extracts_json_surrounded_by_prose():
    assert extract_json('Sure! {"intent": "outlier"} — let me know.') == {"intent": "outlier"}


def test_handles_nested_objects_and_braces_in_strings():
    raw = '{"intent": "ranking", "columns": {"group": "a}b", "metric": "c"}}'
    assert extract_json(raw)["columns"]["group"] == "a}b"


@pytest.mark.parametrize("raw", ["", "   ", "no json at all", "{unclosed: ", "{'single': 'quotes'}"])
def test_rejects_unusable_output(raw):
    with pytest.raises(StructuredOutputError):
        extract_json(raw)


def test_parse_structured_retries_then_succeeds(scripted_client):
    client = scripted_client("not json", '{"intent": "ranking", "limit": 2}')
    result = parse_structured(client, "prompt", "system", Plan)
    assert result.intent == "ranking" and result.limit == 2
    assert len(client.calls) == 2
    assert "could not be used" in client.calls[1]


def test_parse_structured_raises_after_retry(scripted_client):
    client = scripted_client("nope", "still nope")
    with pytest.raises(StructuredOutputError):
        parse_structured(client, "prompt", "system", Plan)
    assert len(client.calls) == 2


def test_parse_structured_retries_on_validation_failure(scripted_client):
    client = scripted_client('{"limit": 2}', '{"intent": "summary"}')
    assert parse_structured(client, "prompt", "system", Plan).intent == "summary"
