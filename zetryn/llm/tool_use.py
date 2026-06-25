"""LLM-driven tool-use loop (function calling).

`tool_use_loop` lets the model invoke tools mid-conversation. The loop:

1. Sends the current message list (plus tool specs) to the LLM.
2. If the model returns text only, the loop returns.
3. If the model returns `tool_calls`, each call is executed via the
   `ToolRegistry`, the results are appended as `role="tool"` messages,
   and the loop iterates.

`ToolUseNode` wraps the loop for graph usage. The node decides when to
stop (no more tool calls, or `max_iterations` reached) and then either:
- writes the assistant's final text to `state.scratch[output_key]`, OR
- if a `schema` is provided, parses the final text as structured output
  before writing.

Safety:
- `max_iterations` is mandatory (default 6) so a misbehaving model
  cannot run up unbounded LLM cost.
- Tool failures never raise into the graph; `ToolRegistry` always
  returns a `ToolResult(ok=False, error=...)` and that error is fed back
  to the model as the tool result, letting it decide what to do.
- On total LLM failure the node falls back via `fallback_fn` (same
  contract as `LLMNode`), never crashing the run.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from ..core.node import Command
from ..core.state import State
from ..tools.registry import ToolRegistry
from .client import LLMClient
from .structured import _extract_json
from .types import LLMError, LLMResult, Message, StructuredOutputError

PromptFn = Callable[[State], list[Message]]
FallbackFn = Callable[[State, Exception], object | None]


@dataclass
class ToolUseTrace:
    """Inspectable record of one tool-use loop run."""

    iterations: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    final_text: str = ""
    truncated: bool = False  # True if max_iterations was hit


async def tool_use_loop(
    client: LLMClient,
    messages: list[Message],
    registry: ToolRegistry,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_iterations: int = 6,
) -> tuple[LLMResult, ToolUseTrace]:
    """Drive a tool-use conversation until the model stops calling tools.

    Returns the final `LLMResult` (whose `text` is the assistant's final
    answer) and a `ToolUseTrace` recording what happened.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    tool_specs = registry.specs()
    convo = list(messages)
    trace = ToolUseTrace()

    last_result: LLMResult | None = None

    for _ in range(max_iterations):
        trace.iterations += 1
        last_result = await client.complete(
            convo, model=model, temperature=temperature, tools=tool_specs
        )

        if not last_result.tool_calls:
            trace.final_text = last_result.text
            return last_result, trace

        # Append the assistant turn that requested the tool calls.
        convo.append({
            "role": "assistant",
            "content": last_result.text or "",
            "tool_calls": last_result.tool_calls,
        })

        # Execute every tool call and append a tool-role message per result.
        for call in last_result.tool_calls:
            trace.tool_calls.append(call)
            fn = call.get("function") or {}
            name = fn.get("name", "")
            raw_args = fn.get("arguments", "{}")
            try:
                kwargs = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError as exc:
                tool_result = {"ok": False, "error": f"bad arguments JSON: {exc}"}
            else:
                exec_result = await registry.call(name, **kwargs)
                tool_result = {
                    "ok": exec_result.ok,
                    "value": exec_result.value,
                    "error": exec_result.error,
                    "duration_ms": exec_result.duration_ms,
                }
            convo.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": json.dumps(tool_result, default=str),
            })

    # Hit the iteration cap — return whatever the model last said.
    trace.truncated = True
    trace.final_text = last_result.text if last_result is not None else ""
    return last_result or LLMResult(text="", model=model or "", latency_ms=0.0), trace


class ToolUseNode:
    """Graph node that runs `tool_use_loop` and stores the result.

    By default writes the assistant's final text to `scratch[output_key]`.
    If `schema` is provided, the final text is parsed + validated as that
    schema; on validation failure the configured fallback is used and
    `<output_key>__llm_failed` is set, matching `LLMNode` semantics.
    """

    def __init__(
        self,
        name: str,
        client: LLMClient,
        registry: ToolRegistry,
        prompt_fn: PromptFn,
        *,
        schema: type[BaseModel] | None = None,
        output_key: str | None = None,
        fallback_fn: FallbackFn | None = None,
        model: str | None = None,
        max_iterations: int = 6,
        trace_key: str | None = None,
    ) -> None:
        self.name = name
        self._client = client
        self._registry = registry
        self._prompt_fn = prompt_fn
        self._schema = schema
        self._output_key = output_key or name
        self._fallback_fn = fallback_fn
        self._model = model
        self._max_iterations = max_iterations
        self._trace_key = trace_key or f"{self._output_key}__trace"

    async def run(self, state: State) -> Command | None:
        messages = self._prompt_fn(state)
        failed_key = f"{self._output_key}__llm_failed"
        try:
            result, trace = await tool_use_loop(
                self._client,
                messages,
                self._registry,
                model=self._model,
                max_iterations=self._max_iterations,
            )
        except LLMError as exc:
            self._apply_fallback(state, exc, failed_key)
            return None

        state.scratch[self._trace_key] = trace

        if self._schema is None:
            state.scratch[self._output_key] = result.text
            state.scratch[failed_key] = False
            return None

        # Schema-mode: parse the assistant's final text as JSON.
        raw = _extract_json(result.text)
        try:
            data = json.loads(raw)
            value = self._schema.model_validate(data)
            state.scratch[self._output_key] = value
            state.scratch[failed_key] = False
        except (json.JSONDecodeError, ValidationError) as exc:
            self._apply_fallback(
                state,
                StructuredOutputError(
                    f"tool-use loop produced invalid {self._schema.__name__}: {exc}"
                ),
                failed_key,
            )
        return None

    def _apply_fallback(self, state: State, exc: Exception, failed_key: str) -> None:
        fallback = self._fallback_fn(state, exc) if self._fallback_fn else None
        state.scratch[self._output_key] = fallback
        state.scratch[failed_key] = True
