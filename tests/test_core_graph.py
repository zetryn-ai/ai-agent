"""Tests for the M0 core graph engine."""

import pytest

from zetryn.core import (
    END,
    AgentNode,
    Command,
    Graph,
    GraphExecutionError,
    GraphValidationError,
    RuleNode,
    State,
)


def build_linear() -> Graph:
    """a -> b -> END, both mutate scratch."""

    def a(s: State) -> None:
        s.scratch["a"] = 1

    def b(s: State) -> None:
        s.scratch["b"] = s.scratch["a"] + 1
        s.output = s.scratch["b"]

    g = Graph("linear")
    g.add_node(RuleNode("a", a)).add_node(RuleNode("b", b))
    g.add_edge("a", "b").add_edge("b", END)
    g.set_entry("a")
    return g.compile()


async def test_linear_flow_runs_in_order():
    g = build_linear()
    state = await g.run(State(context={}))
    assert state.scratch == {"a": 1, "b": 2}
    assert state.output == 2
    assert [t.node for t in state.trace] == ["a", "b"]


async def test_trace_snapshots_are_before_state():
    g = build_linear()
    state = await g.run(State(context={}))
    # First step snapshot is empty (taken before node 'a' ran).
    assert state.trace[0].scratch_before == {}
    # Second step snapshot has 'a' but not yet 'b'.
    assert state.trace[1].scratch_before == {"a": 1}


async def test_conditional_edges_branch():
    def gate(s: State) -> None:
        s.scratch["ok"] = s.context["value"] > 0

    def accept(s: State) -> None:
        s.output = "accepted"

    def reject(s: State) -> None:
        s.output = "rejected"

    g = Graph("branch")
    g.add_node(RuleNode("gate", gate))
    g.add_node(RuleNode("accept", accept))
    g.add_node(RuleNode("reject", reject))
    g.add_edge("gate", "accept", when=lambda s: s.scratch["ok"])
    g.add_edge("gate", "reject", when=lambda s: not s.scratch["ok"])
    g.add_edge("accept", END)
    g.add_edge("reject", END)
    g.set_entry("gate")
    g.compile()

    assert (await g.run(State(context={"value": 5}))).output == "accepted"
    assert (await g.run(State(context={"value": -1}))).output == "rejected"


async def test_command_goto_overrides_edges():
    def router(s: State) -> Command:
        return Command(update={"routed": True}, goto="target")

    def fallback(s: State) -> None:
        s.output = "fallback"

    def target(s: State) -> None:
        s.output = "target"

    g = Graph("cmd")
    g.add_node(RuleNode("router", router))
    g.add_node(RuleNode("fallback", fallback))
    g.add_node(RuleNode("target", target))
    # Static edge points to fallback, but Command.goto must win.
    g.add_edge("router", "fallback")
    g.add_edge("fallback", END)
    g.add_edge("target", END)
    g.set_entry("router")
    g.compile()

    state = await g.run(State(context={}))
    assert state.output == "target"
    assert state.scratch["routed"] is True


async def test_async_rule_node():
    async def slow(s: State) -> None:
        s.scratch["done"] = True

    g = Graph("async")
    g.add_node(RuleNode("slow", slow)).add_edge("slow", END).set_entry("slow")
    g.compile()
    state = await g.run(State(context={}))
    assert state.scratch["done"] is True


async def test_no_matching_edge_terminates():
    def only(s: State) -> None:
        s.output = "done"

    g = Graph("deadend")
    g.add_node(RuleNode("only", only))
    g.add_edge("only", "only", when=lambda s: False)  # never matches
    g.set_entry("only")
    g.compile()
    state = await g.run(State(context={}))
    assert state.output == "done"
    assert len(state.trace) == 1


# -- validation --------------------------------------------------------------


def test_validate_missing_entry():
    g = Graph("x").add_node(RuleNode("a", lambda s: None))
    with pytest.raises(GraphValidationError, match="no entry"):
        g.compile()


def test_validate_entry_not_registered():
    g = Graph("x").add_node(RuleNode("a", lambda s: None)).set_entry("b")
    with pytest.raises(GraphValidationError, match="not registered"):
        g.compile()


def test_validate_edge_to_unknown_node():
    g = Graph("x").add_node(RuleNode("a", lambda s: None)).set_entry("a")
    g.add_edge("a", "ghost")
    with pytest.raises(GraphValidationError, match="not a registered node"):
        g.compile()


def test_validate_duplicate_node():
    g = Graph("x").add_node(RuleNode("a", lambda s: None))
    with pytest.raises(GraphValidationError, match="duplicate"):
        g.add_node(RuleNode("a", lambda s: None))


def test_validate_unreachable_node_is_warning():
    g = Graph("x")
    g.add_node(RuleNode("a", lambda s: None))
    g.add_node(RuleNode("island", lambda s: None))
    g.add_edge("a", END).set_entry("a")
    g.compile()
    assert any("unreachable" in w for w in g.warnings)


# -- safety ------------------------------------------------------------------


async def test_max_steps_guards_infinite_loop():
    g = Graph("loop")
    g.add_node(RuleNode("a", lambda s: None))
    g.add_edge("a", "a")  # unconditional self-loop
    g.set_entry("a")
    g.compile()
    with pytest.raises(GraphExecutionError, match="max_steps"):
        await g.run(State(context={}), max_steps=10)


async def test_node_exception_is_recorded_and_raised():
    def boom(s: State) -> None:
        raise ValueError("kaboom")

    g = Graph("err")
    g.add_node(RuleNode("boom", boom)).add_edge("boom", END).set_entry("boom")
    g.compile()
    state = State(context={})
    with pytest.raises(GraphExecutionError, match="boom"):
        await g.run(state)
    assert state.trace[-1].error is not None
    assert "kaboom" in state.trace[-1].error


# -- sub-agent ---------------------------------------------------------------


async def test_agent_node_runs_subgraph():
    def inner_work(s: State) -> None:
        s.output = {"score": 0.9}

    inner = Graph("inner")
    inner.add_node(RuleNode("w", inner_work)).add_edge("w", END).set_entry("w")
    inner.compile()

    g = Graph("outer")
    g.add_node(AgentNode("sub", inner, output_key="sub_result"))
    g.add_edge("sub", END).set_entry("sub")
    g.compile()

    state = await g.run(State(context={"token": "abc"}))
    assert state.scratch["sub_result"] == {"score": 0.9}
