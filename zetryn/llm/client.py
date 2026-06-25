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
    """Minimal completion interface.

    ``tools`` accepts a list of OpenAI function-calling specs (the same shape
    `Tool.spec()` returns). When the model decides to call a tool, the
    response's ``tool_calls`` field is populated and ``text`` may be empty.
    Implementations that do not support tool-calling MAY ignore ``tools`` and
    return a normal text completion.
    """

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        tools: list[dict] | None = None,
    ) -> LLMResult: ...

    async def aclose(self) -> None: ...
