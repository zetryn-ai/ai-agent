"""Structured logging hooks.

``logging_hooks`` returns a :class:`Hooks` that emits one JSON line per node event.
By default it writes to stderr; pass your own ``emit`` to route elsewhere (file,
queue, the TS dashboard later). Errors in emission never break the graph (the engine
fires hooks via ``safe_fire``).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from zetryn.core.hooks import Hooks
from zetryn.core.state import State, StepTrace

Emit = Callable[[dict[str, Any]], None]


def _default_emit(record: dict[str, Any]) -> None:
    print(json.dumps(record), file=sys.stderr)


def logging_hooks(emit: Emit | None = None) -> Hooks:
    """Build hooks that log node start/end/error as structured JSON."""
    sink = emit or _default_emit

    def on_start(node: str, state: State) -> None:
        sink({"event": "node_start", "run_id": state.run_id, "node": node})

    def on_end(node: str, state: State, step: StepTrace) -> None:
        sink(
            {
                "event": "node_end",
                "run_id": state.run_id,
                "node": node,
                "duration_ms": round(step.duration_ms, 3),
                "next": step.next,
            }
        )

    def on_error(node: str, state: State, exc: Exception) -> None:
        sink(
            {
                "event": "node_error",
                "run_id": state.run_id,
                "node": node,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

    return Hooks(on_node_start=on_start, on_node_end=on_end, on_node_error=on_error)
