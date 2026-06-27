"""Tests for Early-Stage Dip Buy rule nodes (v0.15.0 / S6)."""

from __future__ import annotations

from strategies import SAMPLE_TOKENS, build_dip_buy
from trading import DipBuyConfig, DipBuyContext, DipBuySnapshot
from zetryn.core import State

_NOW = 1_700_000_000.0


def _snap(event_type="launch", **over) -> DipBuySnapshot:
    base = dict(
        event_type=event_type,
        mint="MINT_X",
        detected_at_ts=_NOW,
        time_since_event_seconds=180.0,   # 3 min in
        price_vs_ath_pct=-0.30,           # 30% below ATH
        sell_pressure_score=0.20,         # calm
        buy_ratio_5m=0.60,                # buys winning
        holder_retention_pct=0.75,        # 75% held through
        unique_buyers_trend=0.30,         # rising
        price_stable_seconds=60.0,        # stable 1 min
    )
    base.update(over)
    return DipBuySnapshot(**base)


def _ctx(snap=None, token=None, **cfg) -> DipBuyContext:
    return DipBuyContext(
        token=token if token is not None else SAMPLE_TOKENS["GOOD"],
        snapshot=snap if snap is not None else _snap(),
        config=DipBuyConfig(**cfg),
    )


# -- fast_safety -------------------------------------------------------------


async def test_fast_safety_aborts_rug():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(token=SAMPLE_TOKENS["RUG"])))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True
    assert [t.node for t in state.trace] == ["fast_safety"]


# -- timing_gate -------------------------------------------------------------


async def test_timing_gate_rejects_too_early():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(snap=_snap(time_since_event_seconds=20.0))))
    assert state.output.action == "skip"
    assert "too early" in state.output.reasons[0]


async def test_timing_gate_rejects_too_late():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(snap=_snap(time_since_event_seconds=999.0))))
    assert state.output.action == "skip"
    assert "too late" in state.output.reasons[0]


async def test_timing_gate_graduation_window():
    g = build_dip_buy()
    # Graduation window is 1800s; 900s in should pass
    state = await g.run(State(context=_ctx(
        snap=_snap(event_type="graduation", time_since_event_seconds=900.0),
        event_type="graduation",
        max_time_since_event_seconds=1800.0,
    )))
    assert state.output.action == "buy"


# -- dip_gate ----------------------------------------------------------------


async def test_dip_gate_rejects_insufficient_dip():
    g = build_dip_buy()
    # Only 5% below ATH — not enough
    state = await g.run(State(context=_ctx(snap=_snap(price_vs_ath_pct=-0.05))))
    assert state.output.action == "skip"
    assert "insufficient dip" in state.output.reasons[0]


async def test_dip_gate_rejects_high_sell_pressure():
    g = build_dip_buy()
    # Sell pressure still at 0.8 — dump not over
    state = await g.run(State(context=_ctx(snap=_snap(sell_pressure_score=0.80))))
    assert state.output.action == "skip"
    assert "sell pressure" in state.output.reasons[0]


# -- recovery_gate -----------------------------------------------------------


async def test_recovery_gate_rejects_low_buy_ratio():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(snap=_snap(buy_ratio_5m=0.30))))
    assert state.output.action == "skip"
    assert "buy_ratio_5m" in state.output.reasons[0]


async def test_recovery_gate_rejects_low_holder_retention():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(snap=_snap(holder_retention_pct=0.30))))
    assert state.output.action == "skip"
    assert "holder_retention" in state.output.reasons[0]


async def test_recovery_gate_rejects_falling_unique_buyers():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(
        snap=_snap(unique_buyers_trend=-0.50),
        min_unique_buyers_trend=0.0,
    )))
    assert state.output.action == "skip"
    assert "unique_buyers_trend" in state.output.reasons[0]


async def test_recovery_gate_rejects_unstable_price():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(snap=_snap(price_stable_seconds=5.0))))
    assert state.output.action == "skip"
    assert "price_stable" in state.output.reasons[0]


# -- market_gate -------------------------------------------------------------


async def test_market_gate_rejects_low_liquidity():
    token = SAMPLE_TOKENS["GOOD"].model_copy(
        update={"market": SAMPLE_TOKENS["GOOD"].market.model_copy(update={"liquidity_usd": 500.0})}
    )
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(token=token)))
    assert state.output.action == "skip"
    assert "liquidity" in state.output.reasons[0]


async def test_market_gate_rejects_high_top10():
    token = SAMPLE_TOKENS["GOOD"].model_copy(
        update={"holders": SAMPLE_TOKENS["GOOD"].holders.model_copy(update={"top10_pct": 0.90})}
    )
    g = build_dip_buy()
    state = await g.run(State(context=_ctx(token=token)))
    assert state.output.action == "skip"
    assert "top10_pct" in state.output.reasons[0]


# -- rule_size_and_buy -------------------------------------------------------


async def test_all_gates_pass_emits_buy():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx()))
    d = state.output
    assert d.action == "buy"
    assert d.size is not None and 0 < d.size <= DipBuyConfig().max_size
    assert 0.0 <= d.confidence <= 1.0
    nodes = [t.node for t in state.trace]
    assert nodes == ["fast_safety", "timing_gate", "dip_gate", "recovery_gate", "market_gate", "rule_buy"]


async def test_deeper_dip_produces_larger_size():
    g = build_dip_buy()
    s_shallow = await g.run(State(context=_ctx(snap=_snap(price_vs_ath_pct=-0.15))))
    s_deep = await g.run(State(context=_ctx(snap=_snap(price_vs_ath_pct=-0.60))))
    assert s_deep.output.size > s_shallow.output.size


async def test_lower_sell_pressure_produces_larger_size():
    g = build_dip_buy()
    s_high = await g.run(State(context=_ctx(snap=_snap(sell_pressure_score=0.30))))
    s_low = await g.run(State(context=_ctx(snap=_snap(sell_pressure_score=0.05))))
    assert s_low.output.size > s_high.output.size
