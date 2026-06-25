"""Tests for the M1 LLM layer (no network; MockTransport + fakes)."""

import httpx
import pytest
from pydantic import BaseModel, Field

from zetryn.core import Graph, State
from zetryn.llm import (
    KeyPool,
    LLMError,
    LLMNode,
    NoKeysAvailableError,
    OpenAICompatibleClient,
    ProviderConfig,
    StructuredOutputError,
    structured_complete,
    user,
)
from zetryn.llm.types import LLMResult, Message

# -- KeyPool -----------------------------------------------------------------


def test_keypool_round_robin():
    pool = KeyPool(["k1", "k2", "k3"])
    assert [pool.acquire() for _ in range(4)] == ["k1", "k2", "k3", "k1"]


def test_keypool_skips_penalized_key():
    pool = KeyPool(["k1", "k2"], cooldown_s=999)
    pool.penalize("k1")
    assert pool.acquire() == "k2"
    assert pool.acquire() == "k2"
    assert pool.available() == 1


def test_keypool_all_cooling_raises():
    pool = KeyPool(["k1"], cooldown_s=999)
    pool.penalize("k1")
    with pytest.raises(NoKeysAvailableError):
        pool.acquire()


def test_keypool_requires_keys():
    with pytest.raises(ValueError):
        KeyPool([])


# -- ProviderConfig fail-fast ------------------------------------------------


def test_resolve_keys_fail_fast_when_missing():
    cfg = ProviderConfig("groq", "http://x", "m", key_envs=["MISSING_A", "MISSING_B"])
    with pytest.raises(LLMError, match="none of"):
        cfg.resolve_keys(environ={})


def test_resolve_keys_collects_present():
    cfg = ProviderConfig("groq", "http://x", "m", key_envs=["A", "B", "C"])
    keys = cfg.resolve_keys(environ={"A": "1", "C": "3"})
    assert keys == ["1", "3"]


# -- OpenAICompatibleClient with MockTransport -------------------------------


def _chat_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "fake-model",
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )


async def test_client_completes_successfully():
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_response("hello")

    cfg = ProviderConfig("t", "http://test/v1", "fake-model", key_envs=["K"])
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(cfg, key_pool=KeyPool(["k1"]), http_client=http)

    result = await client.complete([user("hi")])
    assert result.text == "hello"
    assert result.prompt_tokens == 10
    await http.aclose()


async def test_client_rotates_key_on_429():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": "rate"})
        return _chat_response("recovered")

    cfg = ProviderConfig("t", "http://test/v1", "m", key_envs=["K"], max_retries=3)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(cfg, key_pool=KeyPool(["k1", "k2"]), http_client=http)

    result = await client.complete([user("hi")])
    assert result.text == "recovered"
    assert result.key_rotations == 1
    await http.aclose()


async def test_client_rotates_through_all_keys_until_one_succeeds():
    """3-key pool, first two return 429, third recovers — pool order matters."""
    seen_keys: list[str] = []
    behaviour = {"k1": 429, "k2": 429, "k3": 200}

    def handler(request: httpx.Request) -> httpx.Response:
        token = request.headers["Authorization"].removeprefix("Bearer ")
        seen_keys.append(token)
        status = behaviour[token]
        if status == 429:
            return httpx.Response(429, json={"error": "rate"})
        return _chat_response("recovered")

    cfg = ProviderConfig("t", "http://test/v1", "m", key_envs=["K"], max_retries=5)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(
        cfg, key_pool=KeyPool(["k1", "k2", "k3"]), http_client=http
    )

    result = await client.complete([user("hi")])
    assert result.text == "recovered"
    # All three keys were tried in round-robin order before recovery.
    assert seen_keys == ["k1", "k2", "k3"]
    assert result.key_rotations == 2
    await http.aclose()


async def test_client_exhaust_all_keys_then_recovers_after_cooldown(monkeypatch):
    """When every key is on cooldown, the client raises NoKeysAvailable
    via the configured retry budget instead of hanging.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate"})

    cfg = ProviderConfig(
        "t", "http://test/v1", "m", key_envs=["K"],
        max_retries=2,  # 2 attempts → both fail
        cooldown_s=999.0,  # effectively permanent for the test
    )
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(
        cfg, key_pool=KeyPool(["k1", "k2"], cooldown_s=999.0), http_client=http
    )

    with pytest.raises(LLMError, match="completion failed"):
        await client.complete([user("hi")])
    await http.aclose()


async def test_client_succeeds_after_429_then_500_then_200():
    """Mixed transient errors: rate-limit then server error then OK.
    Verifies both 429 (key penalty + rotate) and 5xx (backoff + retry) paths.
    """
    sequence = [429, 500, 200]
    idx = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        status = sequence[idx["i"]]
        idx["i"] += 1
        if status == 200:
            return _chat_response("finally")
        return httpx.Response(status, json={"error": "transient"})

    cfg = ProviderConfig("t", "http://test/v1", "m", key_envs=["K"], max_retries=5)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(
        cfg, key_pool=KeyPool(["k1", "k2"]), http_client=http
    )

    result = await client.complete([user("hi")])
    assert result.text == "finally"
    assert result.key_rotations == 1  # only the 429 caused a rotation
    await http.aclose()


async def test_client_raises_on_4xx():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    cfg = ProviderConfig("t", "http://test/v1", "m", key_envs=["K"])
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(cfg, key_pool=KeyPool(["k1"]), http_client=http)
    with pytest.raises(LLMError, match="400"):
        await client.complete([user("hi")])
    await http.aclose()


# -- structured_complete -----------------------------------------------------


class Score(BaseModel):
    score: float = Field(ge=0, le=1)
    label: str


class _FakeClient:
    """Returns canned texts in sequence; records calls."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self.calls = 0

    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        text = self._texts[min(self.calls, len(self._texts) - 1)]
        self.calls += 1
        return LLMResult(text=text, model="fake", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


async def test_structured_complete_parses_valid_json():
    client = _FakeClient(['{"score": 0.8, "label": "bullish"}'])
    out = await structured_complete(client, [user("rate")], Score)
    assert out.score == 0.8 and out.label == "bullish"


async def test_structured_complete_strips_fences():
    client = _FakeClient(['```json\n{"score": 0.5, "label": "neutral"}\n```'])
    out = await structured_complete(client, [user("rate")], Score)
    assert out.label == "neutral"


async def test_structured_complete_retries_then_succeeds():
    client = _FakeClient(["not json", '{"score": 0.3, "label": "bearish"}'])
    out = await structured_complete(client, [user("rate")], Score, max_attempts=3)
    assert out.score == 0.3
    assert client.calls == 2


async def test_structured_complete_exhausts_and_raises():
    client = _FakeClient(["nope"])
    with pytest.raises(StructuredOutputError):
        await structured_complete(client, [user("rate")], Score, max_attempts=2)


# -- LLMNode graceful fallback ----------------------------------------------


class _RaisingClient:
    async def complete(self, messages, **kw):
        raise LLMError("provider down")

    async def aclose(self):
        pass


async def test_llmnode_stores_result_on_success():
    client = _FakeClient(['{"score": 0.9, "label": "bullish"}'])
    node = LLMNode(
        "scorer", client, Score, lambda s: [user(s.context["q"])], output_key="score"
    )
    state = State(context={"q": "rate this"})
    await node.run(state)
    assert state.scratch["score"].score == 0.9
    assert state.scratch["score__llm_failed"] is False


async def test_llmnode_falls_back_without_crashing():
    def fallback(state, exc):
        return Score(score=0.5, label="neutral")

    node = LLMNode(
        "scorer",
        _RaisingClient(),
        Score,
        lambda s: [user("x")],
        output_key="score",
        fallback_fn=fallback,
    )
    state = State(context={})
    await node.run(state)  # must not raise
    assert state.scratch["score"].label == "neutral"
    assert state.scratch["score__llm_failed"] is True


async def test_llmnode_inside_graph():
    client = _FakeClient(['{"score": 0.7, "label": "bullish"}'])
    g = Graph("g")
    g.add_node(
        LLMNode("scorer", client, Score, lambda s: [user("x")], output_key="score")
    )
    from zetryn.core import END

    g.add_edge("scorer", END).set_entry("scorer").compile()
    state = await g.run(State(context={}))
    assert state.scratch["score"].score == 0.7
