"""Tests for the M2 generic tool system."""

import asyncio

import pytest
from pydantic import BaseModel

from zetryn.tools import Tool, ToolRegistry, tool


async def test_tool_runs_sync_fn():
    t = Tool("add", "add two", lambda a, b: a + b)
    res = await t.call(a=2, b=3)
    assert res.ok and res.value == 5


async def test_tool_runs_async_fn():
    async def fetch(x):
        return x * 2

    t = Tool("fetch", "double", fetch)
    res = await t.call(x=10)
    assert res.ok and res.value == 20


async def test_tool_graceful_on_exception():
    def boom():
        raise RuntimeError("nope")

    res = await Tool("boom", "explodes", boom).call()
    assert res.ok is False
    assert "nope" in res.error


async def test_tool_timeout():
    async def slow():
        await asyncio.sleep(1)

    res = await Tool("slow", "hangs", slow, timeout_s=0.01).call()
    assert res.ok is False
    assert "timeout" in res.error


async def test_tool_validates_input_schema():
    class Args(BaseModel):
        mint: str
        limit: int

    t = Tool("q", "query", lambda mint, limit: f"{mint}:{limit}", input_schema=Args)
    ok = await t.call(mint="abc", limit=5)
    assert ok.value == "abc:5"
    bad = await t.call(mint="abc")  # missing limit
    assert bad.ok is False
    assert "invalid input" in bad.error


def test_tool_decorator_and_spec():
    @tool("sentiment", "get sentiment")
    def sentiment(symbol: str) -> str:
        return "bullish"

    assert isinstance(sentiment, Tool)
    spec = sentiment.spec()
    assert spec["function"]["name"] == "sentiment"


async def test_registry_register_and_call():
    reg = ToolRegistry([Tool("a", "a", lambda: 1)])
    reg.register(Tool("b", "b", lambda: 2))
    assert set(reg.names()) == {"a", "b"}
    assert (await reg.call("a")).value == 1


async def test_registry_unknown_tool_is_graceful():
    reg = ToolRegistry()
    res = await reg.call("ghost")
    assert res.ok is False and "unknown" in res.error


def test_registry_rejects_duplicate():
    reg = ToolRegistry([Tool("a", "a", lambda: 1)])
    with pytest.raises(ValueError, match="duplicate"):
        reg.register(Tool("a", "a", lambda: 2))
