"""Structured output: force a model to return a validated Pydantic object.

Strategy that works across strong and weak models alike: request JSON mode where
supported, instruct the schema in the prompt, parse leniently, validate with
Pydantic, and retry by feeding the validation error back to the model.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .client import LLMClient
from .types import LLMError, Message, StructuredOutputError, system, user

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> str:
    """Best-effort extraction of a JSON object from model output."""
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


async def structured_complete(
    client: LLMClient,
    messages: list[Message],
    schema: type[T],
    *,
    model: str | None = None,
    max_attempts: int = 3,
) -> T:
    """Return a validated instance of ``schema`` from the model."""
    schema_json = json.dumps(schema.model_json_schema(), separators=(",", ":"))
    instruction = system(
        "You are a precise data extractor. Respond with a SINGLE JSON object that "
        "strictly matches this JSON schema. No prose, no markdown fences.\n"
        f"Schema: {schema_json}"
    )
    convo: list[Message] = [instruction, *messages]
    last_error: Exception | None = None

    for _ in range(max_attempts):
        result = await client.complete(convo, model=model, json_mode=True)
        raw = _extract_json(result.text)
        try:
            data = json.loads(raw)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            convo = [
                *convo,
                user(
                    "Your previous response was invalid: "
                    f"{exc}. Return ONLY a corrected JSON object matching the schema."
                ),
            ]
        except LLMError:
            raise

    raise StructuredOutputError(
        f"model did not produce valid {schema.__name__} after {max_attempts} "
        f"attempts: {last_error}"
    )
