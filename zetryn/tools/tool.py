"""Generic tool abstraction.

A tool is an open-ended capability an LLM/agent node may invoke. Tools are
injected by the caller; the framework only defines the shape and runs them safely.

Two safety guarantees, both required for live trading:
- **Timeout** — a slow tool can never hang the hot loop.
- **Graceful errors** — a failing tool returns a result with ``ok=False`` instead
  of raising, so a graph can decide conservatively rather than crash.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

ToolFn = Callable[..., Any] | Callable[..., Awaitable[Any]]


@dataclass
class ToolResult:
    """Outcome of a tool call. Never raised — always returned."""

    ok: bool
    value: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class Tool:
    """A named, safely-callable capability with an optional input schema."""

    def __init__(
        self,
        name: str,
        description: str,
        fn: ToolFn,
        *,
        input_schema: type[BaseModel] | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        self.name = name
        self.description = description
        self._fn = fn
        self.input_schema = input_schema
        self.timeout_s = timeout_s

    async def call(self, **kwargs: Any) -> ToolResult:
        import time

        if self.input_schema is not None:
            try:
                validated = self.input_schema(**kwargs)
                kwargs = validated.model_dump()
            except ValidationError as exc:
                return ToolResult(ok=False, error=f"invalid input: {exc}")

        t0 = time.perf_counter()
        try:
            result = self._fn(**kwargs)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=self.timeout_s)
            value = result
        except TimeoutError:
            return ToolResult(
                ok=False,
                error=f"timeout after {self.timeout_s}s",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:  # noqa: BLE001 - tools must never crash the graph
            return ToolResult(
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        return ToolResult(ok=True, value=value, duration_ms=(time.perf_counter() - t0) * 1000)

    def spec(self) -> dict[str, Any]:
        """OpenAI function-calling spec (for future LLM tool-use loops)."""
        params = (
            self.input_schema.model_json_schema()
            if self.input_schema is not None
            else {"type": "object", "properties": {}}
        )
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }


def tool(
    name: str,
    description: str,
    *,
    input_schema: type[BaseModel] | None = None,
    timeout_s: float = 10.0,
) -> Callable[[ToolFn], Tool]:
    """Decorator that wraps a function into a :class:`Tool`."""

    def wrap(fn: ToolFn) -> Tool:
        return Tool(
            name, description, fn, input_schema=input_schema, timeout_s=timeout_s
        )

    return wrap
