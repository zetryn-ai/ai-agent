"""Generic backtest harness.

Runs a compiled graph over a dataset of (id, context) items and collects each
decision + trace, optionally paired with a known outcome. Because the framework is
stateless toward the real world and all I/O is injected, backtest is just "run the
same graph over historical contexts" — no special engine path.

Domain metrics (PnL, win-rate, rug precision) are computed by passing a scorer to
``BacktestResult.metrics`` — the harness stays domain-agnostic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..core.graph import Graph
from ..core.state import State
from ..observability.trace import trace_to_dicts


@dataclass
class RunRecord:
    """One backtested item: the decision produced and the known outcome (if any)."""

    item_id: str
    decision: Any
    trace: list[dict] = field(default_factory=list)
    outcome: Any | None = None
    error: str | None = None


# A metrics function reduces all records into a summary dict.
MetricsFn = Callable[[list[RunRecord]], dict[str, Any]]


@dataclass
class BacktestResult:
    records: list[RunRecord]

    @property
    def ok(self) -> list[RunRecord]:
        return [r for r in self.records if r.error is None]

    def action_distribution(self) -> dict[str, int]:
        """Domain-agnostic: count decisions by their ``action`` attribute/key."""
        dist: dict[str, int] = {}
        for r in self.ok:
            action = _get(r.decision, "action", "unknown")
            dist[action] = dist.get(action, 0) + 1
        return dist

    def metrics(self, scorer: MetricsFn) -> dict[str, Any]:
        return scorer(self.ok)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a pydantic model, dataclass, dict, or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class Backtester:
    """Runs a graph over a dataset and returns a :class:`BacktestResult`."""

    def __init__(self, graph: Graph) -> None:
        self._graph = graph

    async def run(
        self,
        items: list[tuple[str, Any]],
        *,
        outcomes: dict[str, Any] | None = None,
        max_steps: int = 100,
    ) -> BacktestResult:
        outcomes = outcomes or {}
        records: list[RunRecord] = []
        for item_id, context in items:
            try:
                state = await self._graph.run(State(context=context), max_steps=max_steps)
                records.append(
                    RunRecord(
                        item_id=item_id,
                        decision=state.output,
                        trace=trace_to_dicts(state),
                        outcome=outcomes.get(item_id),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - record failures, keep going
                records.append(
                    RunRecord(item_id=item_id, decision=None, error=f"{type(exc).__name__}: {exc}")
                )
        return BacktestResult(records=records)
