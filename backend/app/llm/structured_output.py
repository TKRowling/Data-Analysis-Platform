"""Coax a strict JSON object out of a chat model and validate it against a Pydantic model.

Local models wrap JSON in prose or code fences and occasionally emit invalid syntax.
This module extracts, validates, and gives the model exactly one corrective retry.
Failure raises - callers are expected to fall back to a deterministic path.
"""
from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


class StructuredOutputError(RuntimeError):
    """The model did not return usable JSON after a retry."""


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of arbitrary model output."""
    if not text or not text.strip():
        raise StructuredOutputError("Model returned an empty response")
    fenced = FENCE.search(text)
    candidate = fenced.group(1).strip() if fenced else text.strip()
    start = candidate.find("{")
    if start == -1:
        raise StructuredOutputError("No JSON object found in model output")
    depth, in_string, escaped = 0, False, False
    for index in range(start, len(candidate)):
        char = candidate[index]
        if in_string:
            if escaped: escaped = False
            elif char == "\\": escaped = True
            elif char == '"': in_string = False
            continue
        if char == '"': in_string = True
        elif char == "{": depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                blob = candidate[start:index + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError as exc:
                    raise StructuredOutputError(f"Malformed JSON: {exc}") from exc
    raise StructuredOutputError("JSON object was never closed")


def parse_structured(client, prompt: str, system: str, model: type[T]) -> T:
    """Ask the model for JSON matching ``model``, retrying once with the validation error."""
    raw = client.complete(prompt, system=system)
    try:
        return model.model_validate(extract_json(raw))
    except (StructuredOutputError, ValidationError) as first_error:
        retry_prompt = (
            f"{prompt}\n\nYour previous reply could not be used.\n"
            f"Error: {first_error}\n"
            f"Previous reply: {raw[:500]}\n\n"
            "Reply with ONLY a valid JSON object. No prose, no code fences."
        )
        retry = client.complete(retry_prompt, system=system)
        try:
            return model.model_validate(extract_json(retry))
        except (StructuredOutputError, ValidationError) as second_error:
            raise StructuredOutputError(f"Model failed to produce valid JSON: {second_error}") from second_error
