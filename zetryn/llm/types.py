"""Shared LLM types, message helpers, and errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# OpenAI-style chat message. Kept as a plain dict for direct wire compatibility.
Message = dict[str, str]


def system(content: str) -> Message:
    return {"role": "system", "content": content}


def user(content: str) -> Message:
    return {"role": "user", "content": content}


def assistant(content: str) -> Message:
    return {"role": "assistant", "content": content}


@dataclass
class LLMResult:
    """Result of a single LLM completion."""

    text: str
    model: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    key_rotations: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMError(Exception):
    """Base error for the LLM layer."""


class LLMTimeoutError(LLMError):
    """The provider did not respond within the timeout."""


class LLMRateLimitError(LLMError):
    """The provider returned 429; key rotation/backoff exhausted."""


class NoKeysAvailableError(LLMError):
    """Every key in the pool is cooling down."""


class StructuredOutputError(LLMError):
    """The model failed to return output matching the schema after retries."""
