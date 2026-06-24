"""Engine lifecycle hooks.

Lightweight seam for observability: the engine fires these around each node so
loggers/metrics can attach without touching the engine. Hooks live in core (the
engine invokes them); concrete implementations live in :mod:`zetryn.observability`.

A hook that raises never breaks execution — its error is swallowed.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import State, StepTrace

StartHook = Callable[[str, "State"], None]
EndHook = Callable[[str, "State", "StepTrace"], None]
ErrorHook = Callable[[str, "State", Exception], None]


@dataclass
class Hooks:
    """Optional callbacks fired around each node. Sync or async are both fine."""

    on_node_start: StartHook | None = None
    on_node_end: EndHook | None = None
    on_node_error: ErrorHook | None = None


async def safe_fire(cb: Callable | None, *args: object) -> None:
    """Invoke a hook callback, swallowing any error so it can't break the graph."""
    if cb is None:
        return
    try:
        result = cb(*args)
        if inspect.isawaitable(result):
            await result
    except Exception:  # noqa: BLE001 - observability must never break execution
        pass
