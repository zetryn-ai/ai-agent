"""v1.4.0 sniper-v2: weighted scoring engine + stagnation exit."""

import pytest

from strategies.agents.lifecycle import build_lifecycle
from strategies.agents.sniper import build_sniper
from trading.schemas import (
    ActivityData,
    ContractData,
    HolderData,
    LifecycleConfig,
    MarketData,
    PositionContext,
    PositionState,
    PumpfunData,
    SniperConfig,
    TokenInput,
    TradingContext,
    WalletIntel,
)
from zetryn.core import State


def _token(**over) -> TokenInput:
    base = dict(
        mint="M",
        symbol="AAA",
        name="aaa",
        source="pumpfun_ws",
        market=MarketData(mcap=50_000, liquidity_usd=6_000, volume_1h=6_000),
        activity=ActivityData(volume_1m_usd=4_000, buys_5m=80, sells_5m=15),
        holders=HolderData(count=120, top10_pct=0.15),
        contract=ContractData(),
        wallets=WalletIntel(smart_wallet_buys=4, kol_wallet_count=1, safety_score=80),
        pumpfun=PumpfunData(
            curve_sol=20,
            curve_velocity_sol_per_min=3.0,
            has_website=True,
            has_twitter=True,
            has_telegram=True,
        ),
    )
    base.update(over)
    return TokenInput(**base)


def _cfg(**over) -> SniperConfig:
    base = dict(
        use_scoring=True,
        min_liquidity_usd=3_000,
        min_volume_1h=0,
        max_mcap_usd=150_000,
        min_volume_1m=1_000,
        min_buy_ratio=0.5,
        min_curve_velocity_sol_per_min=1.0,
    )
    base.update(over)
    return SniperConfig(**base)


async def _run(token, cfg):
    g = build_sniper(llm_client=None)
    state = await g.run(State(context=TradingContext(token=token, config=cfg)))
    return state.output


@pytest.mark.asyncio
async def test_strong_token_auto_buys_with_scored_confidence():
    d = await _run(_token(), _cfg())
    assert d.action == "buy"
    assert d.scores["sniper_score"] >= 90
    assert d.confidence >= 0.9
    assert "auto-buy" in d.reasons[0]


@pytest.mark.asyncio
async def test_mid_score_takes_half_size():
    weak = _token(
        wallets=WalletIntel(),  # no smart money / KOL / safety data
        pumpfun=PumpfunData(),  # no socials / velocity
    )
    d = await _run(weak, _cfg())
    assert d.action in ("buy", "watch")
    if d.action == "buy":
        assert "small-buy" in d.reasons[0]
        full = await _run(_token(), _cfg())
        assert d.size < full.size


@pytest.mark.asyncio
async def test_tax_hard_rejects_regardless_of_score():
    taxed = _token(contract=ContractData(buy_tax_pct=25))
    d = await _run(taxed, _cfg())
    assert d.action == "abort"
    assert "tax" in d.reasons[0]


@pytest.mark.asyncio
async def test_concentrated_top10_drags_score_down():
    heavy = _token(holders=HolderData(count=120, top10_pct=0.55))
    d = await _run(heavy, _cfg(max_top10_pct=1.0))
    assert d.scores["sniper_score"] < 90


@pytest.mark.asyncio
async def test_use_scoring_off_keeps_legacy_v1_behaviour():
    d = await _run(_token(), SniperConfig(min_volume_1h=0))
    assert d.action == "buy"
    assert d.confidence == 0.6  # legacy fixed confidence
    assert "pure-rule entry" in d.reasons[0]


@pytest.mark.asyncio
async def test_stagnation_exit_frees_dead_capital():
    g = build_lifecycle()
    ctx = PositionContext(
        token=TokenInput(mint="M", symbol="AAA"),
        position=PositionState(
            entry_price=1.0,
            entry_size=0.1,
            entry_ts=0.0,
            current_price=1.01,
            current_size=0.1,
            pnl_pct=0.01,
            holding_seconds=400,
            peak_pnl_pct=0.02,
            drawdown_from_peak_pct=0.0,
        ),
        config=LifecycleConfig(stagnation_after_s=300, stagnation_max_pnl_pct=0.05),
    )
    state = await g.run(State(context=ctx))
    assert state.output.action == "exit_full"
    assert "stagnation" in state.output.reasons[0]
