"""Helpers to turn a run's trace into serializable data."""

from __future__ import annotations

from typing import Any

from zetryn.core.state import State


def trace_to_dicts(state: State) -> list[dict[str, Any]]:
    """Serialize the per-node trace (without the scratch snapshots, which may hold
    non-serializable objects)."""
    return [
        {
            "node": t.node,
            "duration_ms": round(t.duration_ms, 3),
            "goto": t.goto,
            "next": t.next,
            "error": t.error,
        }
        for t in state.trace
    ]


def run_summary(state: State) -> dict[str, Any]:
    """A compact, loggable summary of a finished run."""
    return {
        "run_id": state.run_id,
        "steps": len(state.trace),
        "path": [t.node for t in state.trace],
        "latency_ms": round(sum(t.duration_ms for t in state.trace), 3),
        "errors": [t.error for t in state.trace if t.error],
    }
