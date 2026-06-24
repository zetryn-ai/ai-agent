"""LLMNode — an advisor step backed by an LLM with structured output.

Lives in the llm layer (not core) because it depends on an LLM client. Embodies
the advisor contract: on total LLM failure it does NOT crash — it writes a neutral
fallback plus an ``<key>__llm_failed`` flag so downstream rule nodes can decide
conservatively.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from ..core.node import Command
from ..core.state import END, State
from .client import LLMClient
from .structured import structured_complete
from .types import LLMError, Message

PromptFn = Callable[[State], list[Message]]
FallbackFn = Callable[[State, Exception], BaseModel | None]

# Maps a validated LLM model + state to the final decision object.
ResultFn = Callable[[BaseModel, State], Any]
# Optional deterministic guardrail applied to the LLM's decision (hybrid mode).
GuardrailFn = Callable[[Any, State], Any]
# Builds a safe fallback decision when the LLM is unavailable.
DecisionFallbackFn = Callable[[State, Exception], Any]


class LLMNode:
    """Calls an LLM advisor and stores a validated result into scratch."""

    def __init__(
        self,
        name: str,
        client: LLMClient,
        schema: type[BaseModel],
        prompt_fn: PromptFn,
        *,
        output_key: str | None = None,
        fallback_fn: FallbackFn | None = None,
        model: str | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.name = name
        self._client = client
        self._schema = schema
        self._prompt_fn = prompt_fn
        self._output_key = output_key or name
        self._fallback_fn = fallback_fn
        self._model = model
        self._max_attempts = max_attempts

    async def run(self, state: State) -> Command | None:
        messages = self._prompt_fn(state)
        failed_key = f"{self._output_key}__llm_failed"
        try:
            result = await structured_complete(
                self._client,
                messages,
                self._schema,
                model=self._model,
                max_attempts=self._max_attempts,
            )
            state.scratch[self._output_key] = result
            state.scratch[failed_key] = False
        except LLMError as exc:
            # Graceful fallback: never crash the graph on LLM failure.
            fallback = self._fallback_fn(state, exc) if self._fallback_fn else None
            state.scratch[self._output_key] = fallback
            state.scratch[failed_key] = True
        return None


class LLMDecisionNode:
    """Lets the LLM decide directly: its structured output becomes the final
    decision (``state.output``) and the graph ends.

    Modes:
    - **decide**: LLM output → decision, used as-is.
    - **hybrid**: pass a ``guardrail_fn`` that clamps/vetoes the LLM decision with
      deterministic rules (e.g. force abort on rug risk, cap position size). This is
      the recommended mode for real money — the LLM has freedom *inside* the rails.

    On LLM failure it applies ``fallback_fn`` (default: a conservative decision the
    caller supplies) and still ends cleanly — never crashes.
    """

    def __init__(
        self,
        name: str,
        client: LLMClient,
        schema: type[BaseModel],
        prompt_fn: PromptFn,
        result_fn: ResultFn,
        *,
        guardrail_fn: GuardrailFn | None = None,
        fallback_fn: DecisionFallbackFn | None = None,
        model: str | None = None,
        max_attempts: int = 3,
        goto: str = END,
    ) -> None:
        self.name = name
        self._client = client
        self._schema = schema
        self._prompt_fn = prompt_fn
        self._result_fn = result_fn
        self._guardrail_fn = guardrail_fn
        self._fallback_fn = fallback_fn
        self._model = model
        self._max_attempts = max_attempts
        self._goto = goto

    async def run(self, state: State) -> Command | None:
        try:
            result = await structured_complete(
                self._client,
                self._prompt_fn(state),
                self._schema,
                model=self._model,
                max_attempts=self._max_attempts,
            )
            decision = self._result_fn(result, state)
            state.scratch[f"{self.name}__llm_failed"] = False
        except LLMError as exc:
            decision = self._fallback_fn(state, exc) if self._fallback_fn else None
            state.scratch[f"{self.name}__llm_failed"] = True

        # Guardrails apply in every case (including fallback) — rules always win.
        if self._guardrail_fn is not None:
            decision = self._guardrail_fn(decision, state)

        state.output = decision
        return Command(goto=self._goto)
