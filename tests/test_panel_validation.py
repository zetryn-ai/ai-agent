"""Construction-time validation of PanelNode / PanelDecisionNode."""

from __future__ import annotations

import pytest

from zetryn.core.graph import Graph
from zetryn.core.node import RuleNode
from zetryn.panel import PanelDecisionNode, PanelNode


def _trivial_specialist(name: str = "noop") -> Graph:
    g = Graph(name)
    g.add_node(RuleNode(name, lambda s: None))
    g.set_entry(name)
    g.compile()
    return g


def _agg(results, state):
    return results


def test_empty_specialists_rejected():
    with pytest.raises(ValueError, match="non-empty dict"):
        PanelNode("p", specialists={}, aggregator=_agg)


def test_non_graph_specialist_rejected():
    with pytest.raises(TypeError, match="must be a Graph"):
        PanelNode("p", specialists={"bad": "not a graph"}, aggregator=_agg)  # type: ignore[dict-item]


def test_non_callable_aggregator_rejected():
    with pytest.raises(TypeError, match="aggregator"):
        PanelNode("p", specialists={"a": _trivial_specialist()}, aggregator="nope")  # type: ignore[arg-type]


def test_invalid_mode_rejected():
    with pytest.raises(ValueError, match="'mode' must be"):
        PanelNode(
            "p", specialists={"a": _trivial_specialist()},
            aggregator=_agg, mode="dag",  # type: ignore[arg-type]
        )


def test_parallel_with_short_circuit_rejected():
    with pytest.raises(ValueError, match="only meaningful in sequential"):
        PanelNode(
            "p", specialists={"a": _trivial_specialist()},
            aggregator=_agg, mode="parallel",
            short_circuit_on=lambda r, s: None,
        )


def test_required_with_unknown_specialist_rejected():
    with pytest.raises(ValueError, match="'required' names not in specialists"):
        PanelNode(
            "p", specialists={"a": _trivial_specialist()},
            aggregator=_agg, required=["a", "ghost"],
        )


def test_short_circuit_must_be_callable():
    with pytest.raises(TypeError, match="short_circuit_on"):
        PanelNode(
            "p", specialists={"a": _trivial_specialist()},
            aggregator=_agg, mode="sequential",
            short_circuit_on="not callable",  # type: ignore[arg-type]
        )


def test_decision_node_runs_same_validators():
    """Construction-time guards apply equally to PanelDecisionNode."""
    with pytest.raises(ValueError, match="non-empty dict"):
        PanelDecisionNode("d", specialists={}, aggregator=_agg)


def test_node_name_must_be_non_empty():
    with pytest.raises(ValueError, match="non-empty string"):
        PanelNode("", specialists={"a": _trivial_specialist()}, aggregator=_agg)
