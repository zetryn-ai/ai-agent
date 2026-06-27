"""Sequential-mode behavior of PanelNode (including short-circuit)."""

from __future__ import annotations

from typing import Any

import pytest

from zetryn.core.graph import Graph
from zetryn.core.node import RuleNode
from zetryn.core.state import Command, State
from zetryn.panel import PanelExecutionError, PanelNode


# --- Specialist builders ---------------------------------------------------


def _const_specialist(name: str, output: Any) -> Graph:
    def emit(state: State) -> Command | None:
        state.output = output
        return None

    g = Graph(name)
    g.add_node(RuleNode(name, emit))
    g.set_entry(name)
    g.compile()
    return g


def _failing_specialist(name: str, exc: Exception) -> Graph:
    def boom(state: State) -> Command | None:
        raise exc

    g = Graph(name)
    g.add_node(RuleNode(name, boom))
    g.set_entry(name)
    g.compile()
    return g


def _peek_panel_specialist(name: str) -> Graph:
    def emit(state: State) -> Command | None:
        state.output = {"saw": dict(state.scratch.get("_panel", {}))}
        return None

    g = Graph(name)
    g.add_node(RuleNode(name, emit))
    g.set_entry(name)
    g.compile()
    return g


def _identity_aggregator(results: dict[str, Any], state: State) -> dict[str, Any]:
    return results


# --- Tests ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequential_happy_path():
    panel = PanelNode(
        "panel",
        specialists={
            "first":  _const_specialist("a_s", 1),
            "second": _const_specialist("b_s", 2),
            "third":  _const_specialist("c_s", 3),
        },
        aggregator=_identity_aggregator,
        mode="sequential",
    )
    state = State()
    await panel.run(state)
    assert state.scratch["panel"] == {"first": 1, "second": 2, "third": 3}


@pytest.mark.asyncio
async def test_sequential_panel_channel_propagates_prior_results():
    """Specialist N must see all specialists 1..N-1 via scratch['_panel']."""
    panel = PanelNode(
        "panel",
        specialists={
            "a": _peek_panel_specialist("a_s"),
            "b": _peek_panel_specialist("b_s"),
            "c": _peek_panel_specialist("c_s"),
        },
        aggregator=_identity_aggregator,
        mode="sequential",
    )
    state = State()
    await panel.run(state)

    saw = state.scratch["panel"]
    assert saw["a"]["saw"] == {}
    assert saw["b"]["saw"] == {"a": {"saw": {}}}
    assert set(saw["c"]["saw"]) == {"a", "b"}


@pytest.mark.asyncio
async def test_sequential_short_circuit_value_skips_aggregator_and_remaining():
    """Short-circuit value becomes the panel output; aggregator NOT called;
    remaining specialists NOT executed."""

    aggregator_called = []

    def agg(results: dict, state: State) -> Any:
        aggregator_called.append(True)
        return "aggregated"

    ran = []

    def make_tracking(name: str, out: Any) -> Graph:
        def emit(state: State) -> Command | None:
            ran.append(name)
            state.output = out
            return None

        g = Graph(name)
        g.add_node(RuleNode(name, emit))
        g.set_entry(name)
        g.compile()
        return g

    def sc(results: dict, state: State) -> Any | None:
        # After "safety" returns "rug", short-circuit with skip verdict.
        if results.get("safety") == "rug":
            return {"action": "skip", "reason": "rug"}
        return None

    panel = PanelNode(
        "panel",
        specialists={
            "safety": make_tracking("safety", "rug"),
            "market": make_tracking("market", {"score": 0.9}),
            "social": make_tracking("social", {"buzz": "ok"}),
        },
        aggregator=agg,
        mode="sequential",
        short_circuit_on=sc,
    )
    state = State()
    await panel.run(state)

    assert ran == ["safety"]  # market + social never ran
    assert aggregator_called == []  # aggregator never called
    assert state.scratch["panel"] == {"action": "skip", "reason": "rug"}


@pytest.mark.asyncio
async def test_sequential_short_circuit_none_continues():
    """Returning None from short_circuit_on continues normally."""

    def sc(results: dict, state: State) -> Any | None:
        return None  # never short-circuit

    panel = PanelNode(
        "panel",
        specialists={
            "a": _const_specialist("a_s", 1),
            "b": _const_specialist("b_s", 2),
        },
        aggregator=_identity_aggregator,
        mode="sequential",
        short_circuit_on=sc,
    )
    state = State()
    await panel.run(state)
    assert state.scratch["panel"] == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_sequential_required_failure_raises_immediately():
    """Required specialist failure aborts; later specialists do NOT run."""
    later_ran = []

    def make_later(name: str) -> Graph:
        def emit(state: State) -> Command | None:
            later_ran.append(name)
            return None

        g = Graph(name)
        g.add_node(RuleNode(name, emit))
        g.set_entry(name)
        g.compile()
        return g

    panel = PanelNode(
        "panel",
        specialists={
            "must":  _failing_specialist("must_s", RuntimeError("x")),
            "later": make_later("later_s"),
        },
        aggregator=_identity_aggregator,
        mode="sequential",
        required=["must"],
    )
    with pytest.raises(PanelExecutionError):
        await panel.run(State())
    assert later_ran == []


@pytest.mark.asyncio
async def test_sequential_optional_failure_records_and_continues():
    panel = PanelNode(
        "panel",
        specialists={
            "broken": _failing_specialist("b_s", RuntimeError("oops")),
            "after":  _const_specialist("a_s", "done"),
        },
        aggregator=_identity_aggregator,
        mode="sequential",
    )
    state = State()
    await panel.run(state)
    assert state.scratch["panel"]["broken"] is None
    assert state.scratch["panel"]["after"] == "done"
    assert "broken" in state.scratch["_panel_failures"]["panel"]
