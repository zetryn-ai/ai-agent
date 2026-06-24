"""Conditional transitions between nodes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .state import State

# A predicate over the current state. ``None`` means an unconditional edge.
Condition = Callable[[State], bool]


@dataclass
class Edge:
    """A directed, optionally conditional transition.

    The engine evaluates a node's outgoing edges in declaration order and follows
    the first whose ``when`` returns True (or is ``None``). ``target`` may be the
    ``END`` sentinel to stop the graph.
    """

    source: str
    target: str
    when: Condition | None = None

    def matches(self, state: State) -> bool:
        return self.when is None or bool(self.when(state))
