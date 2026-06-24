"""Tests for the M4 observability layer (hooks, logging, trace export)."""

from zetryn.core import END, Graph, Hooks, RuleNode, State
from zetryn.observability import logging_hooks, run_summary, trace_to_dicts


def _simple_graph() -> Graph:
    g = Graph("g")
    g.add_node(RuleNode("a", lambda s: s.scratch.__setitem__("a", 1)))
    g.add_node(RuleNode("b", lambda s: s.scratch.__setitem__("b", 2)))
    g.add_edge("a", "b").add_edge("b", END).set_entry("a")
    return g.compile()


async def test_hooks_fire_in_order():
    events: list[str] = []
    hooks = Hooks(
        on_node_start=lambda n, s: events.append(f"start:{n}"),
        on_node_end=lambda n, s, t: events.append(f"end:{n}"),
    )
    await _simple_graph().run(State(context={}), hooks=hooks)
    assert events == ["start:a", "end:a", "start:b", "end:b"]


async def test_hook_error_does_not_break_graph():
    def boom(n, s):
        raise RuntimeError("hook blew up")

    hooks = Hooks(on_node_start=boom)
    state = await _simple_graph().run(State(context={}), hooks=hooks)
    assert state.scratch == {"a": 1, "b": 2}  # graph still completed


async def test_error_hook_fires_on_node_failure():
    captured: list[str] = []

    def fail(s):
        raise ValueError("nope")

    g = Graph("e")
    g.add_node(RuleNode("x", fail)).add_edge("x", END).set_entry("x").compile()
    hooks = Hooks(on_node_error=lambda n, s, e: captured.append(str(e)))
    from zetryn.core import GraphExecutionError

    try:
        await g.run(State(context={}), hooks=hooks)
    except GraphExecutionError:
        pass
    assert captured and "nope" in captured[0]


async def test_async_hook_supported():
    seen: list[str] = []

    async def on_end(n, s, t):
        seen.append(n)

    await _simple_graph().run(State(context={}), hooks=Hooks(on_node_end=on_end))
    assert seen == ["a", "b"]


async def test_logging_hooks_emit_json_records():
    records: list[dict] = []
    hooks = logging_hooks(emit=records.append)
    await _simple_graph().run(State(context={}), hooks=hooks)
    events = [r["event"] for r in records]
    assert events == ["node_start", "node_end", "node_start", "node_end"]
    assert all("run_id" in r for r in records)


async def test_trace_export_helpers():
    state = await _simple_graph().run(State(context={}))
    dicts = trace_to_dicts(state)
    assert [d["node"] for d in dicts] == ["a", "b"]
    summary = run_summary(state)
    assert summary["path"] == ["a", "b"]
    assert summary["steps"] == 2
    assert summary["errors"] == []
