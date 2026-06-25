"""Tests for the multi-provider LLM router."""

from __future__ import annotations

import pytest

from zetryn.auth.subscription import RateLimit
from zetryn.llm import (
    PROVIDER_FREE_TIER_LIMITS,
    LLMRouter,
    RouterEntry,
    get_free_tier_limit,
)
from zetryn.llm.types import (
    LLMError,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
    Message,
    NoKeysAvailableError,
)


class FakeClient:
    """Scriptable LLMClient for tests."""

    def __init__(self, *, responses: list, name: str = "fake") -> None:
        self._responses = list(responses)
        self.name = name
        self.calls = 0
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
        if not self._responses:
            raise LLMError(f"{self.name}: no scripted responses left")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        self.closed = True


def _result(text: str = "ok", *, prompt: int = 10, completion: int = 5) -> LLMResult:
    return LLMResult(
        text=text,
        model="m",
        latency_ms=1.0,
        prompt_tokens=prompt,
        completion_tokens=completion,
    )


# -- Failover --------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_uses_first_available():
    a = FakeClient(responses=[_result("a")])
    b = FakeClient(responses=[_result("b")])
    router = LLMRouter([a, b])
    result = await router.complete([{"role": "user", "content": "hi"}])
    assert result.text == "a"
    assert a.calls == 1
    assert b.calls == 0


@pytest.mark.asyncio
async def test_router_fails_over_on_rate_limit():
    a = FakeClient(responses=[LLMRateLimitError("429")])
    b = FakeClient(responses=[_result("b")])
    router = LLMRouter([a, b])
    result = await router.complete([{"role": "user", "content": "hi"}])
    assert result.text == "b"
    assert a.calls == 1
    assert b.calls == 1


@pytest.mark.asyncio
async def test_router_fails_over_on_no_keys():
    a = FakeClient(responses=[NoKeysAvailableError("dry")])
    b = FakeClient(responses=[_result("b")])
    router = LLMRouter([a, b])
    assert (await router.complete([{"role": "user", "content": "hi"}])).text == "b"


@pytest.mark.asyncio
async def test_router_fails_over_on_timeout():
    a = FakeClient(responses=[LLMTimeoutError("slow")])
    b = FakeClient(responses=[_result("b")])
    router = LLMRouter([a, b])
    assert (await router.complete([{"role": "user", "content": "hi"}])).text == "b"


@pytest.mark.asyncio
async def test_router_exhaustion_raises():
    a = FakeClient(responses=[LLMRateLimitError("429")])
    b = FakeClient(responses=[LLMRateLimitError("429")])
    router = LLMRouter([a, b])
    with pytest.raises(LLMError):
        await router.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_router_skips_cooled_entry_on_next_call():
    a = FakeClient(responses=[LLMRateLimitError("429"), _result("a-recovered")])
    b = FakeClient(responses=[_result("b1"), _result("b2")])
    router = LLMRouter([a, b], cooldown_s=999)

    r1 = await router.complete([{"role": "user", "content": "1"}])
    assert r1.text == "b1"  # fell over to b
    assert a.calls == 1

    r2 = await router.complete([{"role": "user", "content": "2"}])
    # a is still cooling — must skip without calling
    assert r2.text == "b2"
    assert a.calls == 1  # no extra call to a


# -- Throttle --------------------------------------------------------------


@pytest.mark.asyncio
async def test_throttle_rpm_blocks_overuse():
    a = FakeClient(responses=[_result("a1"), _result("a2"), _result("a3")])
    b = FakeClient(responses=[_result("b1")])
    router = LLMRouter(
        [
            RouterEntry(client=a, name="a", limit=RateLimit(rpm=2)),
            RouterEntry(client=b, name="b"),
        ]
    )
    assert (await router.complete([{"role": "user", "content": "1"}])).text == "a1"
    assert (await router.complete([{"role": "user", "content": "2"}])).text == "a2"
    # third request hits rpm=2 on a, must fall over to b
    assert (await router.complete([{"role": "user", "content": "3"}])).text == "b1"
    assert a.calls == 2
    assert b.calls == 1


@pytest.mark.asyncio
async def test_throttle_tpm_blocks_overuse():
    a = FakeClient(
        responses=[_result("a1", prompt=50, completion=50)]
    )  # 100 tokens
    b = FakeClient(responses=[_result("b1")])
    router = LLMRouter(
        [
            RouterEntry(client=a, name="a", limit=RateLimit(tpm=100)),
            RouterEntry(client=b, name="b"),
        ]
    )
    assert (await router.complete([{"role": "user", "content": "1"}])).text == "a1"
    # tpm exhausted on a
    assert (await router.complete([{"role": "user", "content": "2"}])).text == "b1"
    assert a.calls == 1


@pytest.mark.asyncio
async def test_throttle_rpd_blocks_overuse():
    a = FakeClient(responses=[_result("a1"), _result("a2")])
    b = FakeClient(responses=[_result("b1")])
    router = LLMRouter(
        [
            RouterEntry(client=a, name="a", limit=RateLimit(rpd=1)),
            RouterEntry(client=b, name="b"),
        ]
    )
    assert (await router.complete([{"role": "user", "content": "1"}])).text == "a1"
    assert (await router.complete([{"role": "user", "content": "2"}])).text == "b1"


@pytest.mark.asyncio
async def test_all_throttled_raises_no_keys():
    a = FakeClient(responses=[_result("a1")])
    b = FakeClient(responses=[_result("b1")])
    router = LLMRouter(
        [
            RouterEntry(client=a, name="a", limit=RateLimit(rpm=1)),
            RouterEntry(client=b, name="b", limit=RateLimit(rpm=1)),
        ]
    )
    await router.complete([{"role": "user", "content": "1"}])
    await router.complete([{"role": "user", "content": "2"}])
    with pytest.raises(NoKeysAvailableError):
        await router.complete([{"role": "user", "content": "3"}])


# -- Cleanup ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_aclose_propagates():
    a = FakeClient(responses=[])
    b = FakeClient(responses=[])
    router = LLMRouter([a, b])
    await router.aclose()
    assert a.closed and b.closed


def test_router_requires_entries():
    with pytest.raises(ValueError):
        LLMRouter([])


def test_provider_free_tier_presets_have_expected_providers():
    assert {"groq", "openrouter", "gemini"} <= PROVIDER_FREE_TIER_LIMITS.keys()
    for provider, table in PROVIDER_FREE_TIER_LIMITS.items():
        assert table, f"{provider} has no model entries"
        for model_id, limit in table.items():
            assert limit.rpm is None or limit.rpm > 0, (provider, model_id)
            assert limit.rpd is None or limit.rpd > 0, (provider, model_id)


def test_get_free_tier_limit_exact_match():
    limit = get_free_tier_limit("groq", "llama-3.1-8b-instant")
    assert limit is not None and limit.rpm == 30 and limit.tpd == 500_000


def test_get_free_tier_limit_openrouter_free_suffix():
    a = get_free_tier_limit("openrouter", "meta-llama/llama-3.3-70b-instruct:free")
    b = get_free_tier_limit("openrouter", "qwen/qwen3-coder:free")
    assert a is not None and b is not None
    assert a.rpm == 20 and a.rpd == 50
    assert a is b  # same shared preset


def test_get_free_tier_limit_unknown_returns_none():
    assert get_free_tier_limit("unknown-provider", "x") is None
    assert get_free_tier_limit("groq", "definitely-not-a-model") is None
    # openrouter without :free suffix should also miss
    assert get_free_tier_limit("openrouter", "openai/gpt-4o") is None


@pytest.mark.asyncio
async def test_preset_can_be_attached_to_entry():
    a = FakeClient(responses=[_result("a1")])
    preset = get_free_tier_limit("groq", "llama-3.1-8b-instant")
    entry = RouterEntry(client=a, name="groq", limit=preset)
    router = LLMRouter([entry])
    result = await router.complete([{"role": "user", "content": "hi"}])
    assert result.text == "a1"
    assert entry.limit is preset


@pytest.mark.asyncio
async def test_throttle_tpd_blocks_overuse():
    a = FakeClient(responses=[_result("a1", prompt=600, completion=400)])  # 1000 tok
    b = FakeClient(responses=[_result("b1")])
    router = LLMRouter(
        [
            RouterEntry(client=a, name="a", limit=RateLimit(tpd=1_000)),
            RouterEntry(client=b, name="b"),
        ]
    )
    assert (await router.complete([{"role": "user", "content": "1"}])).text == "a1"
    # tpd exhausted on a (used 1000, limit 1000)
    assert (await router.complete([{"role": "user", "content": "2"}])).text == "b1"
    assert a.calls == 1
