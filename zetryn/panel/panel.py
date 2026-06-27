"""PanelNode + PanelDecisionNode — rule-orchestrated multi-specialist nodes.

Both node types run a fixed set of specialist sub-graphs (parallel or
sequential), then call a user-supplied aggregator that merges the per-
specialist outputs into a single value. The difference is where that value
lands:

- :class:`PanelNode` writes it to ``state.scratch[output_key]`` and continues
  via the graph's static edges.
- :class:`PanelDecisionNode` writes it to ``state.output`` and returns
  ``Command(goto=...)`` to terminate (or jump elsewhere).

State scoping (decision #4 in the design doc):
- Each specialist runs in an isolated ``State(context=parent.context,
  scratch={"_panel": <prior_results>})``.
- In ``parallel`` mode, ``_panel`` is always empty (no prior).
- In ``sequential`` mode, ``_panel`` is a snapshot of completed specialists'
  outputs.

Failure handling (decision #6):
- Failure of a specialist whose name is in ``required`` raises
  :class:`PanelExecutionError`.
- Failure of any other specialist is recorded — ``results[name] = None``,
  ``state.scratch["_panel_failures"][panel_name][name] = "<ExcType>: <msg>"``.
- ``short_circuit_on`` (sequential only) gets ``(results, state)`` after each
  specialist; if it returns non-None that value becomes the panel output and
  the aggregator is **not** called.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Any, Literal

from ..core.graph import Graph
from ..core.state import END, Command, State

Aggregator = Callable[[dict[str, Any], State], Any]
ShortCircuitFn = Callable[[dict[str, Any], State], Any | None]

_VALID_MODES = ("parallel", "sequential")


class PanelExecutionError(Exception):
    """Raised when a specialist listed in ``required`` fails."""


# ----- Shared validation + runtime ------------------------------------------


def _validate_construction(
    name: str,
    specialists: dict[str, Graph],
    aggregator: Any,
    *,
    mode: str,
    required: Sequence[str],
    short_circuit_on: Any,
) -> None:
    if not isinstance(name, str) or not name:
        raise ValueError("panel node 'name' must be a non-empty string")
    if not isinstance(specialists, dict) or not specialists:
        raise ValueError(
            "panel 'specialists' must be a non-empty dict[str, Graph]"
        )
    for spec_name, graph in specialists.items():
        if not isinstance(spec_name, str) or not spec_name:
            raise ValueError(
                "every specialist key must be a non-empty string"
            )
        if not isinstance(graph, Graph):
            raise TypeError(
                f"specialist {spec_name!r} must be a Graph, "
                f"got {type(graph).__name__}"
            )
    if not callable(aggregator):
        raise TypeError("'aggregator' must be callable")
    if mode not in _VALID_MODES:
        raise ValueError(
            f"'mode' must be one of {_VALID_MODES}, got {mode!r}"
        )
    if short_circuit_on is not None and not callable(short_circuit_on):
        raise TypeError("'short_circuit_on' must be callable or None")
    if mode == "parallel" and short_circuit_on is not None:
        raise ValueError(
            "'short_circuit_on' is only meaningful in sequential mode "
            "(in parallel mode all specialists are already in flight)"
        )
    required_tuple = tuple(required)
    unknown = [r for r in required_tuple if r not in specialists]
    if unknown:
        raise ValueError(
            f"'required' names not in specialists: {unknown} "
            f"(available: {sorted(specialists)})"
        )


async def _run_one(name: str, graph: Graph, sub_state: State) -> tuple[str, Any | None, Exception | None]:
    """Run a single specialist sub-graph, capturing exceptions for caller."""
    try:
        final = await graph.run(sub_state)
        return name, final.output, None
    except Exception as exc:  # noqa: BLE001 — graceful per-specialist failure
        return name, None, exc


async def _run_panel(
    panel_name: str,
    specialists: dict[str, Graph],
    state: State,
    *,
    mode: str,
    required: tuple[str, ...],
    short_circuit_on: ShortCircuitFn | None,
) -> tuple[dict[str, Any], dict[str, str], Any | None]:
    """Execute the specialist sub-graphs.

    Returns ``(results, failures, short_circuit_value)``. The aggregator is
    NOT called here — that's the responsibility of the calling node so it
    can route the final value to scratch vs state.output.
    """
    results: dict[str, Any] = {}
    failures: dict[str, str] = {}
    sc_value: Any | None = None

    if mode == "parallel":
        # All specialists see an empty _panel — no prior results.
        outcomes = await asyncio.gather(
            *(
                _run_one(
                    n,
                    g,
                    State(context=state.context, scratch={"_panel": {}}),
                )
                for n, g in specialists.items()
            )
        )
        # Rebuild results in specialists' declared insertion order for stability.
        outcome_by_name = {n: (out, exc) for n, out, exc in outcomes}
        for n in specialists:
            out, exc = outcome_by_name[n]
            if exc is not None:
                if n in required:
                    raise PanelExecutionError(
                        f"required specialist {n!r} failed: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                failures[n] = f"{type(exc).__name__}: {exc}"
                results[n] = None
            else:
                results[n] = out
        return results, failures, None

    # sequential
    for n, g in specialists.items():
        sub_state = State(
            context=state.context,
            scratch={"_panel": dict(results)},
        )
        _, out, exc = await _run_one(n, g, sub_state)
        if exc is not None:
            if n in required:
                raise PanelExecutionError(
                    f"required specialist {n!r} failed: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            failures[n] = f"{type(exc).__name__}: {exc}"
            results[n] = None
        else:
            results[n] = out

        if short_circuit_on is not None:
            sc = short_circuit_on(results, state)
            if sc is not None:
                sc_value = sc
                break

    return results, failures, sc_value


def _record_failures(state: State, panel_name: str, failures: dict[str, str]) -> None:
    """Stash failure info into ``state.scratch["_panel_failures"][panel_name]``."""
    if not failures:
        return
    bucket = state.scratch.get("_panel_failures")
    if not isinstance(bucket, dict):
        bucket = {}
        state.scratch["_panel_failures"] = bucket
    bucket[panel_name] = failures


# ----- Public node classes --------------------------------------------------


class PanelNode:
    """Intermediate panel — aggregator result goes to ``scratch[output_key]``.

    Use this when the panel produces an intermediate verdict consumed by
    later nodes in the graph. For a panel that ends the graph with a final
    Decision, use :class:`PanelDecisionNode` instead.
    """

    def __init__(
        self,
        name: str,
        specialists: dict[str, Graph],
        aggregator: Aggregator,
        *,
        mode: Literal["parallel", "sequential"] = "parallel",
        output_key: str | None = None,
        required: Sequence[str] = (),
        short_circuit_on: ShortCircuitFn | None = None,
    ) -> None:
        _validate_construction(
            name, specialists, aggregator,
            mode=mode, required=required, short_circuit_on=short_circuit_on,
        )
        self.name = name
        self._specialists = specialists
        self._aggregator = aggregator
        self._mode = mode
        self._output_key = output_key or name
        self._required = tuple(required)
        self._short_circuit_on = short_circuit_on

    async def run(self, state: State) -> Command | None:
        results, failures, sc = await _run_panel(
            self.name, self._specialists, state,
            mode=self._mode,
            required=self._required,
            short_circuit_on=self._short_circuit_on,
        )
        _record_failures(state, self.name, failures)
        if sc is not None:
            state.scratch[self._output_key] = sc
        else:
            state.scratch[self._output_key] = self._aggregator(results, state)
        return None


class PanelDecisionNode:
    """Terminal panel — aggregator result becomes ``state.output``, graph terminates.

    Mirrors :class:`zetryn.llm.node.LLMDecisionNode`: the panel's verdict is
    the final answer; the node returns ``Command(goto=...)`` to terminate
    (default ``END``).
    """

    def __init__(
        self,
        name: str,
        specialists: dict[str, Graph],
        aggregator: Aggregator,
        *,
        mode: Literal["parallel", "sequential"] = "parallel",
        goto: str = END,
        required: Sequence[str] = (),
        short_circuit_on: ShortCircuitFn | None = None,
    ) -> None:
        _validate_construction(
            name, specialists, aggregator,
            mode=mode, required=required, short_circuit_on=short_circuit_on,
        )
        self.name = name
        self._specialists = specialists
        self._aggregator = aggregator
        self._mode = mode
        self._goto = goto
        self._required = tuple(required)
        self._short_circuit_on = short_circuit_on

    async def run(self, state: State) -> Command | None:
        results, failures, sc = await _run_panel(
            self.name, self._specialists, state,
            mode=self._mode,
            required=self._required,
            short_circuit_on=self._short_circuit_on,
        )
        _record_failures(state, self.name, failures)
        if sc is not None:
            state.output = sc
        else:
            state.output = self._aggregator(results, state)
        return Command(goto=self._goto)
