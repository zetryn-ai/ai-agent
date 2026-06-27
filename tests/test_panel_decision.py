"""PanelDecisionNode — terminal panel, writes state.output and Command(goto=...)."""

from __future__ import annotations

from typing import Any

import pytest

from zetryn.core.graph import Graph
from zetryn.core.node import RuleNode
from zetryn.core.state import END, Command, State
from zetryn.panel import PanelDecisionNode


def _const_specialist(name: str, output: Any) -> Graph:
    def emit(state: State) -> Command | None:
        state.output = output
        return None

    g = Graph(name)
    g.add_node(RuleNode(name, emit))
    g.set_entry(name)
    g.compile()
    return g


def _identity(results: dict[str, Any], state: State) -> dict[str, Any]:
    return results


@pytest.mark.asyncio
async def test_decision_writes_state_output_and_terminates():
    panel = PanelDecisionNode(
        "decide",
        specialists={
            "a": _const_specialist("a_s", 1),
            "b": _const_specialist("b_s", 2),
        },
        aggregator=_identity,
    )
    state = State()
    cmd = await panel.run(state)
    assert state.output == {"a": 1, "b": 2}
    assert cmd is not None
    assert cmd.goto == END


@pytest.mark.asyncio
async def test_decision_custom_goto():
    panel = PanelDecisionNode(
        "decide",
        specialists={"a": _const_specialist("a_s", 1)},
        aggregator=_identity,
        goto="next_node",
    )
    cmd = await panel.run(State())
    assert cmd is not None
    assert cmd.goto == "next_node"


@pytest.mark.asyncio
async def test_decision_short_circuit_value_becomes_output():
    """When short-circuit fires, its value lands in state.output (not aggregator)."""

    def sc(results: dict, state: State) -> Any | None:
        if results.get("safety") == "rug":
            return {"action": "skip"}
        return None

    aggregator_called = []

    def agg(results: dict, state: State) -> Any:
        aggregator_called.append(True)
        return "agg"

    panel = PanelDecisionNode(
        "decide",
        specialists={
            "safety": _const_specialist("safety_s", "rug"),
            "market": _const_specialist("market_s", {"score": 1.0}),
        },
        aggregator=agg,
        mode="sequential",
        short_circuit_on=sc,
    )
    state = State()
    cmd = await panel.run(state)
    assert state.output == {"action": "skip"}
    assert aggregator_called == []
    assert cmd is not None
    assert cmd.goto == END


@pytest.mark.asyncio
async def test_decision_inside_graph_run_terminates():
    """End-to-end: PanelDecisionNode inside a Graph.run() terminates the graph."""
    panel = PanelDecisionNode(
        "decide",
        specialists={"a": _const_specialist("a_s", 42)},
        aggregator=lambda r, s: {"action": "buy", "value": r["a"]},
    )
    g = Graph("test")
    g.add_node(panel)
    g.set_entry("decide")
    g.compile()

    final = await g.run(State())
    assert final.output == {"action": "buy", "value": 42}
