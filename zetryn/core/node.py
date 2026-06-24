"""Node primitives.

A node is the unit of work. Every node exposes the same tiny interface, so the
engine never needs to know what a node contains — this is what makes the "hybrid"
paradigm free: an ``AgentNode`` is just a node that happens to run another graph.

``LLMNode`` lives in :mod:`zetryn.llm` because it depends on an LLM client; keeping
it out of core preserves the rule that core has no external dependencies.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from .state import Command, State


@runtime_checkable
class Node(Protocol):
    """The single interface every node implements."""

    name: str

    async def run(self, state: State) -> Command | None: ...


# A rule function may be sync or async and returns a Command or None.
RuleFn = Callable[[State], Command | None] | Callable[[State], Awaitable[Command | None]]


class RuleNode:
    """Deterministic step backed by a plain Python function.

    The function mutates ``state.scratch`` directly and/or returns a ``Command``
    for dynamic routing. Both sync and async functions are supported.
    """

    def __init__(self, name: str, fn: RuleFn) -> None:
        self.name = name
        self._fn = fn

    async def run(self, state: State) -> Command | None:
        result = self._fn(state)
        if inspect.isawaitable(result):
            result = await result
        return result


@runtime_checkable
class Runnable(Protocol):
    """Anything the engine can execute as a sub-graph (duck-typed Graph)."""

    async def run(self, state: State) -> State: ...


class AgentNode:
    """Extension point: a node whose work is another graph (sub-agent).

    The sub-graph runs with the parent ``context`` and a fresh scratch. Its
    ``output`` is written back into the parent scratch under ``output_key``.
    This is the seam for multi-agent panels; richer coordination is built later.
    """

    def __init__(
        self,
        name: str,
        graph: Runnable,
        *,
        output_key: str | None = None,
        context_fn: Callable[[State], Any] | None = None,
    ) -> None:
        self.name = name
        self._graph = graph
        self._output_key = output_key or name
        self._context_fn = context_fn

    async def run(self, state: State) -> Command | None:
        from .state import State as _State

        inner_context = self._context_fn(state) if self._context_fn else state.context
        inner = _State(context=inner_context)
        result = await self._graph.run(inner)
        return Command(update={self._output_key: result.output})
