"""Tests for graduation snipe rule nodes (v0.12.0)."""

from __future__ import annotations

from strategies import SAMPLE_TOKENS, build_graduation
from trading import (
    ContractData,
    GraduationConfig,
    GraduationContext,
    GraduationEvent,
    HolderData,
    MarketData,
    TokenInput,
)
from zetryn.core import State


def _good_event(**over) -> GraduationEvent:
    base = dict(
        mint="MINT_X",
        pair_address="PAIR_X",
        detected_at_ts=1_700_000_000.0,
        pair_age_seconds=2.0,
        bonding_curve_fill_seconds=120.0,
        bonding_curve_unique_buyers=120,
        bonding_curve_sol_raised=85.0,
        bonding_curve_premium_pct=5.0,
        initial_liquidity_sol=45.0,
        initial_liquidity_token_pct=20.0,
        lp_burned=True,
    )
    base.update(over)
    return GraduationEvent(**base)


def _ctx(event=None, token=None, **cfg) -> GraduationContext:
    return GraduationContext(
        token=token if token is not None else SAMPLE_TOKENS["GOOD"],
        event=event if event is not None else _good_event(),
        config=GraduationConfig(**cfg),
    )


async def test_all_gates_pass_emits_buy():
    g = build_graduation(llm_client=None)
    state = await g.run(State(context=_ctx()))
    d = state.output
    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    nodes = [t.node for t in state.trace]
    assert nodes == ["fast_safety", "graduation_gate", "market_gate", "rule_buy"]


async def test_fast_safety_aborts_dangerous_contract():
    g = build_graduation(llm_client=None)
    state = await g.run(State(context=_ctx(token=SAMPLE_TOKENS["RUG"])))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True
    assert [t.node for t in state.trace] == ["fast_safety"]


async def test_graduation_gate_rejects_lp_not_burned():
    g = build_graduation(llm_client=None)
    state = await g.run(State(context=_ctx(event=_good_event(lp_burned=False))))
    assert state.output.action == "abort"
    assert "LP not burned" in state.output.reasons[0]


async def test_graduation_gate_rejects_pair_too_old():
    g = build_graduation(llm_client=None)
    state = await g.run(State(context=_ctx(event=_good_event(pair_age_seconds=30.0))))
    assert state.output.action == "skip"
    assert "pair_age" in state.output.reasons[0]


async def test_graduation_gate_rejects_slow_fill():
    g = build_graduation(llm_client=None)
    state = await g.run(
        State(context=_ctx(event=_good_event(bonding_curve_fill_seconds=999.0)))
    )
    assert state.output.action == "skip"
    assert "fill" in state.output.reasons[0]


async def test_graduation_gate_rejects_too_few_buyers():
    g = build_graduation(llm_client=None)
    state = await g.run(
        State(context=_ctx(event=_good_event(bonding_curve_unique_buyers=10)))
    )
    assert state.output.action == "skip"
    assert "unique_buyers" in state.output.reasons[0]


async def test_graduation_gate_rejects_thin_initial_liquidity():
    g = build_graduation(llm_client=None)
    state = await g.run(
        State(context=_ctx(event=_good_event(initial_liquidity_sol=5.0)))
    )
    assert state.output.action == "skip"
    assert "initial_liquidity" in state.output.reasons[0]


async def test_graduation_gate_rejects_overpumped():
    g = build_graduation(llm_client=None)
    state = await g.run(
        State(context=_ctx(event=_good_event(bonding_curve_premium_pct=80.0)))
    )
    assert state.output.action == "skip"
    assert "premium" in state.output.reasons[0]


async def test_market_gate_rejects_low_liquidity():
    g = build_graduation(llm_client=None)
    thin = TokenInput(
        mint="THIN",
        symbol="THIN",
        market=MarketData(mcap=10_000, liquidity_usd=500, volume_1h=100),
        holders=HolderData(count=80, top10_pct=0.3),
        contract=ContractData(lp_burned=True),
    )
    state = await g.run(State(context=_ctx(token=thin)))
    assert state.output.action == "skip"
    assert "liquidity" in state.output.reasons[0]


async def test_market_gate_rejects_high_top10():
    g = build_graduation(llm_client=None)
    concentrated = TokenInput(
        mint="CONC",
        symbol="CONC",
        market=MarketData(mcap=100_000, liquidity_usd=20_000, volume_1h=10_000),
        holders=HolderData(count=200, top10_pct=0.85),
        contract=ContractData(lp_burned=True),
    )
    state = await g.run(State(context=_ctx(token=concentrated)))
    assert state.output.action == "skip"
    assert "top10_pct" in state.output.reasons[0]


async def test_size_respects_hard_cap():
    g = build_graduation(llm_client=None)
    state = await g.run(State(context=_ctx(base_size=100.0, max_size=1.5)))
    assert state.output.size is not None and state.output.size <= 1.5
