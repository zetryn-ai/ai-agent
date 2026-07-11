"""Parallel-mode behavior of PanelNode."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from zetryn.core.graph import Graph
from zetryn.core.node import RuleNode
from zetryn.core.state import Command, State
from zetryn.panel import PanelExecutionError, PanelNode


# --- Specialist builders (each returns a Graph) -----------------------------


def _const_specialist(name: str, output: Any) -> Graph:
    """Trivial specialist that writes a constant to state.output."""

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
    """Specialist that records what it saw in scratch['_panel'] at entry."""

    def emit(state: State) -> Command | None:
        state.output = {"saw": dict(state.scratch.get("_panel", {}))}
        return None

    g = Graph(name)
    g.add_node(RuleNode(name, emit))
    g.set_entry(name)
    g.compile()
    return g


# --- Aggregator -------------------------------------------------------------


def _identity_aggregator(results: dict[str, Any], state: State) -> dict[str, Any]:
    return results


# --- Tests ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_happy_path():
    panel = PanelNode(
        "panel",
        specialists={
            "safety": _const_specialist("safety_s", {"verdict": "ok"}),
            "market": _const_specialist("market_s", {"score": 0.8}),
            "social": _const_specialist("social_s", {"buzz": "high"}),
        },
        aggregator=_identity_aggregator,
        mode="parallel",
    )
    state = State()
    await panel.run(state)
    out = state.scratch["panel"]
    assert out == {
        "safety": {"verdict": "ok"},
        "market": {"score": 0.8},
        "social": {"buzz": "high"},
    }


@pytest.mark.asyncio
async def test_parallel_results_isolated_no_panel_leak():
    """Parallel specialists see EMPTY _panel — no sibling leakage."""
    panel = PanelNode(
        "panel",
        specialists={
            "a": _peek_panel_specialist("a"),
            "b": _peek_panel_specialist("b"),
            "c": _peek_panel_specialist("c"),
        },
        aggregator=_identity_aggregator,
        mode="parallel",
    )
    state = State()
    await panel.run(state)
    for name in ("a", "b", "c"):
        assert state.scratch["panel"][name]["saw"] == {}


@pytest.mark.asyncio
async def test_parallel_optional_failure_records_and_continues():
    panel = PanelNode(
        "panel",
        specialists={
            "ok": _const_specialist("ok_s", {"v": 1}),
            "broken": _failing_specialist("broken_s", RuntimeError("kaboom")),
        },
        aggregator=_identity_aggregator,
        mode="parallel",
    )
    state = State()
    await panel.run(state)

    assert state.scratch["panel"]["ok"] == {"v": 1}
    assert state.scratch["panel"]["broken"] is None
    assert "_panel_failures" in state.scratch
    assert state.scratch["_panel_failures"]["panel"]["broken"].startswith(
        "GraphExecutionError"
    )


@pytest.mark.asyncio
async def test_parallel_required_failure_raises_panel_error():
    panel = PanelNode(
        "panel",
        specialists={
            "ok": _const_specialist("ok_s", {"v": 1}),
            "must": _failing_specialist("must_s", RuntimeError("boom")),
        },
        aggregator=_identity_aggregator,
        mode="parallel",
        required=["must"],
    )
    with pytest.raises(PanelExecutionError, match="required specialist 'must'"):
        await panel.run(State())


@pytest.mark.asyncio
async def test_aggregator_receives_state_and_results():
    received: dict[str, Any] = {}

    def agg(results: dict[str, Any], state: State) -> str:
        received["results"] = results
        received["context"] = state.context
        return "merged"

    panel = PanelNode(
        "panel",
        specialists={"x": _const_specialist("x_s", 42)},
        aggregator=agg,
    )
    state = State(context={"meta": "yo"})
    await panel.run(state)

    assert state.scratch["panel"] == "merged"
    assert received["results"] == {"x": 42}
    assert received["context"] == {"meta": "yo"}


@pytest.mark.asyncio
async def test_results_order_matches_declaration_not_finish_time():
    """asyncio.gather order is non-deterministic; aggregator should still
    receive results in specialists' declared insertion order."""

    async def slow(state: State, ms: float) -> None:
        await asyncio.sleep(ms / 1000)
        state.output = ms

    # Build specialists where later-declared finishes faster.
    def build(name: str, ms: float) -> Graph:
        async def fn(state: State) -> Command | None:
            await slow(state, ms)
            return None

        g = Graph(name)
        g.add_node(RuleNode(name, fn))
        g.set_entry(name)
        g.compile()
        return g

    panel = PanelNode(
        "panel",
        specialists={
            "slow":   build("slow_s", 30),
            "medium": build("med_s", 15),
            "fast":   build("fast_s", 1),
        },
        aggregator=_identity_aggregator,
    )
    state = State()
    await panel.run(state)
    assert list(state.scratch["panel"].keys()) == ["slow", "medium", "fast"]


@pytest.mark.asyncio
async def test_output_key_override():
    panel = PanelNode(
        "panel",
        specialists={"a": _const_specialist("a_s", 1)},
        aggregator=_identity_aggregator,
        output_key="custom_bucket",
    )
    state = State()
    await panel.run(state)
    assert state.scratch["custom_bucket"] == {"a": 1}
    assert "panel" not in state.scratch
