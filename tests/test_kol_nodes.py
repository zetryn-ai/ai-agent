"""Tests for K3 — KOL strategy rule nodes (fast_safety, kol_quality,
fast_market, sizing). Pure functions; no LLM, no graph wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from strategies import KOLRegistry
from strategies.nodes.kol_nodes import (
    fast_market,
    fast_safety,
    make_kol_quality,
    sizing,
)
from trading import (
    KOLBuyEvent,
    KOLContext,
    KOLCopyTradeConfig,
    TokenInput,
)
from trading.schemas import ContractData, HolderData, MarketData, WalletIntel
from zetryn.core import State
from zetryn.knowledge import KnowledgePack

# -- fixtures --------------------------------------------------------------


def _token(
    *,
    is_dangerous: bool = False,
    liquidity: float = 10_000,
    volume_1h: float = 8_000,
    top10: float = 0.15,
    bundlers: int = 0,
    snipers: int = 0,
) -> TokenInput:
    return TokenInput(
        mint="M",
        symbol="MEME",
        name="Meme",
        market=MarketData(liquidity_usd=liquidity, volume_1h=volume_1h),
        holders=HolderData(top10_pct=top10),
        contract=ContractData(is_honeypot=is_dangerous),
        wallets=WalletIntel(
            bundler_wallet_count=bundlers, sniper_wallet_count=snipers
        ),
    )


def _event(
    *,
    wallet: str = "ABC",
    sol_amount: float = 1.0,
    detected_at_ts: float = 1000.0,
    block_age_seconds: float = 5.0,
) -> KOLBuyEvent:
    return KOLBuyEvent(
        wallet=wallet, mint="M", sol_amount=sol_amount,
        detected_at_ts=detected_at_ts, block_age_seconds=block_age_seconds,
    )


def _ctx(
    token: TokenInput | None = None,
    event: KOLBuyEvent | None = None,
    config: KOLCopyTradeConfig | None = None,
    last_copy_ts: float | None = None,
) -> KOLContext:
    return KOLContext(
        event=event or _event(),
        token=token or _token(),
        config=config or KOLCopyTradeConfig(),
        last_copy_ts=last_copy_ts,
    )


def _make_pack(tmp_path: Path, wallets: dict, **globals_) -> KnowledgePack:
    data = tmp_path / "data" / "kol_whitelist.json"
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps({"wallets": wallets, **globals_}), encoding="utf-8")
    return KnowledgePack.from_dir(tmp_path)


def _whitelist_with(tmp_path, **overrides):
    """A pack registering ABC as a healthy S-tier KOL by default."""
    profile = {"hit_rate": 0.55, "tier": "S", "name": "smart_money_1"}
    profile.update(overrides)
    pack = _make_pack(tmp_path, wallets={"ABC": profile}, min_hit_rate=0.40)
    return KOLRegistry.from_pack(pack)


# Helper kontekstual: jalankan node terhadap state baru
async def _run(node_fn, ctx: KOLContext):
    state = State(context=ctx)
    cmd = await node_fn(state) if hasattr(node_fn, "__await__") else node_fn(state)
    return state, cmd


# -- fast_safety ------------------------------------------------------------


def test_fast_safety_aborts_on_dangerous_contract():
    state = State(context=_ctx(token=_token(is_dangerous=True)))
    cmd = fast_safety(state)
    assert cmd is not None and cmd.goto == "__end__"
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True


def test_fast_safety_passes_on_safe_contract():
    state = State(context=_ctx())
    assert fast_safety(state) is None
    assert state.output is None


# -- kol_quality ------------------------------------------------------------


@pytest.mark.asyncio
async def test_kol_quality_skips_unknown_wallet(tmp_path):
    reg = _whitelist_with(tmp_path)
    state = State(context=_ctx(event=_event(wallet="UNKNOWN")))
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None and cmd.goto == "__end__"
    assert state.output.action == "skip"
    assert "unknown KOL" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_skips_wallet_below_pack_floor(tmp_path):
    # KOL exists but tier C, pack requires tier ≥ A
    pack = _make_pack(
        tmp_path,
        wallets={"ABC": {"hit_rate": 0.5, "tier": "C"}},
        min_tier_to_copy="A",
        min_hit_rate=0.40,
    )
    reg = KOLRegistry.from_pack(pack)
    state = State(context=_ctx())
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None
    assert "pack floor" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_skips_below_deployment_min_tier(tmp_path):
    # Pack allows tier B, but deployment config requires tier A
    pack = _make_pack(
        tmp_path,
        wallets={"ABC": {"hit_rate": 0.5, "tier": "B"}},
        min_tier_to_copy="B",  # pack-level floor permissive
        min_hit_rate=0.0,
    )
    reg = KOLRegistry.from_pack(pack)
    cfg = KOLCopyTradeConfig(min_kol_tier="A")  # stricter
    state = State(context=_ctx(config=cfg))
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None
    assert "below deployment min A" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_skips_below_deployment_min_hit_rate(tmp_path):
    pack = _make_pack(tmp_path, wallets={"ABC": {"hit_rate": 0.42, "tier": "S"}})
    reg = KOLRegistry.from_pack(pack)
    cfg = KOLCopyTradeConfig(min_kol_hit_rate=0.50)
    state = State(context=_ctx(config=cfg))
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None and "hit_rate" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_skips_when_kol_buy_size_too_small(tmp_path):
    reg = _whitelist_with(tmp_path, min_sol_to_copy=2.0)
    state = State(context=_ctx(event=_event(sol_amount=0.5)))
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None and "buy size" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_skips_stale_signal(tmp_path):
    reg = _whitelist_with(tmp_path)
    state = State(context=_ctx(event=_event(block_age_seconds=60)))
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None and "too stale" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_enforces_cooldown(tmp_path):
    reg = _whitelist_with(tmp_path)
    # Same KOL was copied 10s ago; default cooldown is 60s
    state = State(context=_ctx(
        event=_event(detected_at_ts=1010.0),
        last_copy_ts=1000.0,
    ))
    cmd = make_kol_quality(reg)(state)
    assert cmd is not None and "cooldown" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_kol_quality_passes_healthy_signal_and_stores_profile(tmp_path):
    reg = _whitelist_with(tmp_path)
    state = State(context=_ctx())
    cmd = make_kol_quality(reg)(state)
    assert cmd is None  # no rejection
    assert state.output is None
    assert "kol_profile" in state.scratch
    assert state.scratch["kol_profile"].tier == "S"


# -- fast_market ------------------------------------------------------------


def test_fast_market_skips_low_liquidity():
    state = State(context=_ctx(token=_token(liquidity=100)))
    cmd = fast_market(state)
    assert cmd is not None
    assert "liquidity" in state.output.reasons[0]


def test_fast_market_skips_low_volume():
    state = State(context=_ctx(token=_token(volume_1h=10)))
    cmd = fast_market(state)
    assert cmd is not None and "volume_1h" in state.output.reasons[0]


def test_fast_market_skips_concentrated_holders():
    state = State(context=_ctx(token=_token(top10=0.90)))
    cmd = fast_market(state)
    assert cmd is not None and "top10_pct" in state.output.reasons[0]


def test_fast_market_skips_too_many_bundlers():
    state = State(context=_ctx(token=_token(bundlers=10)))
    cmd = fast_market(state)
    assert cmd is not None and "bundler_count" in state.output.reasons[0]


def test_fast_market_skips_too_many_snipers():
    state = State(context=_ctx(token=_token(snipers=20)))
    cmd = fast_market(state)
    assert cmd is not None and "sniper_count" in state.output.reasons[0]


def test_fast_market_passes_clean_market():
    state = State(context=_ctx())
    assert fast_market(state) is None


# -- sizing ----------------------------------------------------------------


def test_sizing_emits_buy_with_scaled_size():
    """Healthy KOL + clean token → buy with size > base."""
    from trading.schemas import KOLProfile
    state = State(context=_ctx())
    state.scratch["kol_profile"] = KOLProfile(hit_rate=0.7, tier="S")
    sizing(state)
    d = state.output
    assert d is not None and d.action == "buy"
    # hit_rate 0.7 → kol_conf saturates at 1.0 → kol_mult = 3
    # top10=0.15 → top10_pen = 1.0
    # size = 1.0 * 3.0 * 1.0 = 3.0
    assert d.size == 3.0
    assert d.confidence == 1.0
    assert "kol_confidence" in d.scores


def test_sizing_clamps_at_max_size():
    from trading.schemas import KOLProfile
    cfg = KOLCopyTradeConfig(base_size=2.0, max_size=4.0)
    state = State(context=_ctx(config=cfg))
    state.scratch["kol_profile"] = KOLProfile(hit_rate=0.9, tier="S")
    sizing(state)
    assert state.output.size == 4.0  # hits the cap


def test_sizing_penalises_concentrated_holders():
    from trading.schemas import KOLProfile
    state = State(context=_ctx(token=_token(top10=0.50)))
    state.scratch["kol_profile"] = KOLProfile(hit_rate=0.55, tier="S")
    sizing(state)
    # top10 = 0.50 → top10_pen = 1 - (0.50 - 0.20) = 0.70
    # kol_conf at hit_rate=0.55, floor 0.4, ceiling 0.7 → raw=0.5 → kol_conf=0.5
    # kol_mult = 1 + 2*0.5 = 2.0
    # size = 1.0 * 2.0 * 0.70 = 1.4
    assert state.output.size == pytest.approx(1.4, abs=0.001)
