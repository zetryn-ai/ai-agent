"""Core state primitives that flow through a graph.

The engine uses a hybrid model: nodes mutate ``State.scratch`` in place for
ergonomics, while the engine takes an automatic snapshot before every node so the
full ``trace`` is available for audit, resume, and backtest.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any

# Sentinel target meaning "stop the graph". Used by edges and ``Command.goto``.
END = "__end__"


@dataclass
class Command:
    """Dynamic routing escape hatch returned by a node.

    A node may return a ``Command`` to update state and/or override the next node
    at runtime. If a node returns ``None`` instead, the engine falls back to the
    statically declared edges.
    """

    update: dict[str, Any] = field(default_factory=dict)
    goto: str | None = None


@dataclass
class StepTrace:
    """Immutable record of a single node execution."""

    node: str
    scratch_before: dict[str, Any]
    duration_ms: float
    goto: str | None = None
    next: str | None = None
    error: str | None = None


@dataclass
class State:
    """Data flowing through the graph.

    Attributes:
        context: Input supplied by the caller (e.g. a bot's TradingContext). The
            core treats it as opaque.
        scratch: Mutable inter-node working area (scores, flags, analysis).
        output: Final result produced by the graph (e.g. a trading Decision).
        trace: Per-node execution snapshots, appended by the engine.
        run_id: Unique id for this run, for correlating logs.
    """

    context: Any = None
    scratch: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    trace: list[StepTrace] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def snapshot_scratch(self) -> dict[str, Any]:
        """Return a deep copy of the current scratch for tracing."""
        return copy.deepcopy(self.scratch)

    def merge(self, update: dict[str, Any]) -> None:
        """Apply a ``Command.update`` to scratch (shallow merge)."""
        self.scratch.update(update)
