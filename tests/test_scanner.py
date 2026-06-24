"""M8 AI-first scanner end-to-end on sample TokenInput + fake LLM."""

import json

from strategies import SAMPLE_TOKENS, build_scanner
from trading import ScannerConfig, TradingContext
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message


def _full_analysis_payload(
    *, final: float = 0.85, rec: str = "alert", safety_score: float = 0.9
) -> dict:
    aspect = lambda s, v: {  # noqa: E731
        "score": s, "verdict": v, "signals": [], "reasoning": "fake",
    }
    return {
        "safety": aspect(safety_score, "positive"),
        "market": aspect(0.8, "positive"),
        "wallets": aspect(0.7, "positive"),
        "social": aspect(0.7, "positive"),
        "final_score": final,
        "recommendation": rec,
        "reasoning": "fake analyst synthesis",
    }


class _FakeLLM:
    """Returns a fixed FullAnalysis as JSON."""

    def __init__(self, *, final: float = 0.85, rec: str = "alert") -> None:
        self._payload = _full_analysis_payload(final=final, rec=rec)

    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._payload), model="fake", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


def _ctx(mint: str, **cfg) -> TradingContext:
    return TradingContext(token=SAMPLE_TOKENS[mint], config=ScannerConfig(**cfg))


async def test_good_token_alerts_with_llm():
    g = build_scanner(_FakeLLM(final=0.85, rec="alert"))
    state = await g.run(State(context=_ctx("GOOD")))
    d = state.output
    assert d.action == "alert"
    assert d.confidence >= 0.7
    # FullAnalysis populated on Decision
    assert d.analysis is not None
    assert d.analysis.recommendation == "alert"
    # per-aspect scores carried through
    assert {"safety", "market", "wallets", "social", "final"} <= set(d.scores)
    assert d.meta["run_id"] and "latency_ms" in d.meta
    # LLM ran only after passing all hard gates
    assert [t.node for t in state.trace][-2:] == ["analyst", "finalize"]


async def test_rug_token_rejected_before_llm():
    g = build_scanner(_FakeLLM())
    state = await g.run(State(context=_ctx("RUG")))
    assert state.output.action == "skip"
    assert state.output.flags["rug_risk"] is True
    assert state.output.flags.get("hard_gate") is True
    assert "analyst" not in [t.node for t in state.trace]
    assert state.output.analysis is None
    assert any("rug" in r for r in state.output.reasons)


async def test_low_market_rejected_after_safety_before_llm():
    g = build_scanner(_FakeLLM())
    state = await g.run(State(context=_ctx("LOWLIQ")))
    assert state.output.action == "skip"
    assert [t.node for t in state.trace] == [
        "safety_gate", "intel_gate", "market_gate", "reject",
    ]
    assert state.output.analysis is None


async def test_rule_only_scanner_without_client():
    """No LLM = analyst skipped; finalize falls back to neutral skip."""
    g = build_scanner(llm_client=None)
    state = await g.run(State(context=_ctx("GOOD")))
    assert state.output.action in {"alert", "watch", "skip"}
    assert "analyst" not in [t.node for t in state.trace]


async def test_llm_failure_falls_back_to_neutral_skip():
    class _Down:
        async def complete(self, *a, **k):
            from zetryn.llm import LLMError

            raise LLMError("down")

        async def aclose(self):
            pass

    g = build_scanner(_Down())
    state = await g.run(State(context=_ctx("GOOD")))
    assert state.output is not None
    assert state.output.flags["llm_failed"] is True
    # conservative bias: LLM failure -> skip
    assert state.output.action == "skip"
    assert "LLM unavailable" in " ".join(state.output.reasons)


async def test_guardrail_demotes_alert_when_liquidity_far_below_floor():
    """If LLM hallucinates an alert with no liquidity, guardrail demotes to watch."""
    g = build_scanner(_FakeLLM(final=0.9, rec="alert"))
    # HYPE_NOLIQ has $2k liquidity, default min is $5k → guardrail trips.
    # But HYPE_NOLIQ is rejected at market_gate (liq < min), so it never reaches
    # the analyst. To test the guardrail, lower min_liquidity below the token's
    # liquidity (so it lets it through the gate) but still > 2x its liquidity.
    cfg = ScannerConfig(min_liquidity_usd=1_500, min_volume_1h=5_000)
    # token has 2_000 liq; gate passes (>= 1500) but guardrail compares to
    # 1500*0.5=750 → 2000 > 750, no demote. Need liq < 0.5 * min → use a
    # contrived alt: bump min to 5000 so gate would fail. Instead simpler: just
    # validate the guardrail logic via its inputs directly.
    from strategies.nodes.decide import _apply_guardrails
    from trading.schemas import AspectAnalysis, FullAnalysis

    analysis = FullAnalysis(
        safety=AspectAnalysis(score=0.9, verdict="positive"),
        market=AspectAnalysis(score=0.9, verdict="positive"),
        wallets=AspectAnalysis(score=0.9, verdict="positive"),
        social=AspectAnalysis(score=0.9, verdict="positive"),
        final_score=0.9,
        recommendation="alert",
    )

    class _S:
        scratch: dict = {}

        def __init__(self, token, cfg):
            class _C:
                pass
            self.context = _C()
            self.context.token = token
            self.context.config = cfg

    token = SAMPLE_TOKENS["GOOD"].model_copy(deep=True)
    token.market.liquidity_usd = 1_000  # well below the 5000 minimum
    guarded, messages = _apply_guardrails(analysis, _S(token, ScannerConfig()))
    assert guarded.recommendation == "watch"
    assert any("liquidity" in m for m in messages)
    # silence unused fixture warning
    _ = (g, cfg)


async def test_sample_provider_pull_matches_push():
    from strategies import SampleProvider

    provider = SampleProvider()
    token = await provider.fetch("GOOD")
    assert token.mint == "GOOD"
    g = build_scanner(_FakeLLM(final=0.85, rec="alert"))
    state = await g.run(State(context=TradingContext(token=token)))
    assert state.output.action == "alert"
