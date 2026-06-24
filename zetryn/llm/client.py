"""The thin LLM client abstraction.

A single small interface lets nodes stay provider-agnostic. The first concrete
implementation is OpenAI-compatible (Groq / OpenRouter / Gemini); an Anthropic
native client is added later for prompt caching.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import LLMResult, Message


@runtime_checkable
class LLMClient(Protocol):
    """Minimal completion interface."""

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> LLMResult: ...

    async def aclose(self) -> None: ...
