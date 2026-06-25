"""Tests for the LLM tool-use loop and ToolUseNode."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from zetryn.core import State
from zetryn.llm import ToolUseNode, ToolUseTrace, tool_use_loop
from zetryn.llm.types import LLMError, LLMResult, Message
from zetryn.tools import Tool, ToolRegistry

# -- helpers ---------------------------------------------------------------


class _ScriptedClient:
    """Returns canned LLMResult objects in sequence, optionally raising."""

    def __init__(self, results: list) -> None:
        self._results = list(results)
        self.calls = 0
        self.received_tools: list[list[dict] | None] = []
        self.closed = False

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        self.calls += 1
        self.received_tools.append(tools)
        if not self._results:
            raise LLMError("no scripted results left")
        item = self._results.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        self.closed = True


def _result(text: str = "", *, tool_calls: list[dict] | None = None) -> LLMResult:
    return LLMResult(
        text=text,
        model="fake",
        latency_ms=1.0,
        tool_calls=list(tool_calls or []),
    )


def _tool_call(name: str, arguments: dict, call_id: str = "c1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _registry_with_echo() -> ToolRegistry:
    async def echo(value: str) -> str:
        return f"echoed:{value}"

    class _EchoInput(BaseModel):
        value: str

    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo back the value", echo, input_schema=_EchoInput))
    return reg


# -- tool_use_loop ---------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_returns_immediately_when_no_tool_calls():
    client = _ScriptedClient([_result("done")])
    reg = _registry_with_echo()

    result, trace = await tool_use_loop(client, [{"role": "user", "content": "hi"}], reg)
    assert result.text == "done"
    assert trace.iterations == 1
    assert trace.tool_calls == []
    assert trace.final_text == "done"
    assert trace.truncated is False
    # tool specs were forwarded
    assert client.received_tools[0] is not None and len(client.received_tools[0]) == 1


@pytest.mark.asyncio
async def test_loop_executes_tool_and_continues():
    """Model calls echo, sees the result, then produces a final answer."""
    client = _ScriptedClient([
        _result(tool_calls=[_tool_call("echo", {"value": "hi"})]),
        _result("final answer"),
    ])
    reg = _registry_with_echo()

    result, trace = await tool_use_loop(client, [{"role": "user", "content": "hi"}], reg)
    assert result.text == "final answer"
    assert trace.iterations == 2
    assert len(trace.tool_calls) == 1
    assert client.calls == 2


@pytest.mark.asyncio
async def test_loop_feeds_tool_failure_back_to_model():
    """Tool errors do not crash the loop — they become a tool-role message."""
    async def boom(**kw):
        raise RuntimeError("disk on fire")

    reg = ToolRegistry()
    reg.register(Tool("boom", "Always fails", boom))

    client = _ScriptedClient([
        _result(tool_calls=[_tool_call("boom", {})]),
        _result("recovered"),
    ])

    result, trace = await tool_use_loop(client, [{"role": "user", "content": "try"}], reg)
    assert result.text == "recovered"
    assert trace.iterations == 2


@pytest.mark.asyncio
async def test_loop_handles_invalid_json_arguments():
    """A model emitting malformed tool args is reported as tool failure, not crash."""
    async def echo(value: str = ""):
        return value

    reg = ToolRegistry()
    reg.register(Tool("echo", "Echo", echo))

    bad_call = {
        "id": "c1",
        "type": "function",
        "function": {"name": "echo", "arguments": "{not json"},
    }
    client = _ScriptedClient([
        _result(tool_calls=[bad_call]),
        _result("understood"),
    ])

    result, trace = await tool_use_loop(client, [{"role": "user", "content": "x"}], reg)
    assert result.text == "understood"
    assert trace.iterations == 2


@pytest.mark.asyncio
async def test_loop_truncates_at_max_iterations():
    """Model that never stops calling tools is bounded by max_iterations."""
    client = _ScriptedClient([
        _result(tool_calls=[_tool_call("echo", {"value": "a"}, "c1")]),
        _result(tool_calls=[_tool_call("echo", {"value": "b"}, "c2")]),
        _result(tool_calls=[_tool_call("echo", {"value": "c"}, "c3")]),
    ])
    reg = _registry_with_echo()

    result, trace = await tool_use_loop(
        client, [{"role": "user", "content": "x"}], reg, max_iterations=3
    )
    assert trace.truncated is True
    assert trace.iterations == 3
    assert len(trace.tool_calls) == 3
    assert result is not None


@pytest.mark.asyncio
async def test_loop_rejects_invalid_max_iterations():
    with pytest.raises(ValueError):
        await tool_use_loop(_ScriptedClient([]), [], _registry_with_echo(), max_iterations=0)


# -- ToolUseNode -----------------------------------------------------------


@pytest.mark.asyncio
async def test_node_writes_final_text_to_scratch():
    client = _ScriptedClient([_result("hello world")])
    reg = _registry_with_echo()

    node = ToolUseNode(
        "advise", client, reg, prompt_fn=lambda s: [{"role": "user", "content": "hi"}]
    )
    state = State()
    await node.run(state)
    assert state.scratch["advise"] == "hello world"
    assert state.scratch["advise__llm_failed"] is False
    trace = state.scratch["advise__trace"]
    assert isinstance(trace, ToolUseTrace) and trace.iterations == 1


@pytest.mark.asyncio
async def test_node_parses_schema_when_provided():
    class Verdict(BaseModel):
        action: str = Field(...)
        confidence: float = Field(ge=0, le=1)

    payload = json.dumps({"action": "buy", "confidence": 0.8})
    client = _ScriptedClient([_result(payload)])
    reg = _registry_with_echo()

    node = ToolUseNode(
        "advise", client, reg,
        prompt_fn=lambda s: [{"role": "user", "content": "x"}],
        schema=Verdict,
    )
    state = State()
    await node.run(state)
    out = state.scratch["advise"]
    assert isinstance(out, Verdict)
    assert out.action == "buy" and out.confidence == 0.8


@pytest.mark.asyncio
async def test_node_calls_tool_then_returns_schema():
    """Realistic flow: model calls a tool, then emits a final JSON verdict."""

    class Verdict(BaseModel):
        action: str
        reason: str

    client = _ScriptedClient([
        _result(tool_calls=[_tool_call("echo", {"value": "check"})]),
        _result(json.dumps({"action": "alert", "reason": "tool result encouraging"})),
    ])
    reg = _registry_with_echo()

    node = ToolUseNode(
        "advise", client, reg,
        prompt_fn=lambda s: [{"role": "user", "content": "decide"}],
        schema=Verdict,
    )
    state = State()
    await node.run(state)

    assert state.scratch["advise"].action == "alert"
    trace = state.scratch["advise__trace"]
    assert trace.iterations == 2 and len(trace.tool_calls) == 1


@pytest.mark.asyncio
async def test_node_falls_back_on_llm_error():
    """When the loop raises an LLMError, fallback_fn is applied."""
    client = _ScriptedClient([LLMError("provider down")])
    reg = _registry_with_echo()

    def fallback(state: State, exc: Exception) -> str:
        return "safe-default"

    node = ToolUseNode(
        "advise", client, reg,
        prompt_fn=lambda s: [{"role": "user", "content": "x"}],
        fallback_fn=fallback,
    )
    state = State()
    await node.run(state)
    assert state.scratch["advise"] == "safe-default"
    assert state.scratch["advise__llm_failed"] is True


@pytest.mark.asyncio
async def test_node_falls_back_on_schema_validation_error():
    """Malformed final JSON triggers fallback rather than raising."""

    class Verdict(BaseModel):
        action: str

    client = _ScriptedClient([_result("not even close to json")])
    reg = _registry_with_echo()

    node = ToolUseNode(
        "advise", client, reg,
        prompt_fn=lambda s: [{"role": "user", "content": "x"}],
        schema=Verdict,
        fallback_fn=lambda s, exc: "fallback",
    )
    state = State()
    await node.run(state)
    assert state.scratch["advise"] == "fallback"
    assert state.scratch["advise__llm_failed"] is True
