"""K4 end-to-end tests for build_kol_copytrade (rule mode)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from strategies import KOLRegistry, build_kol_copytrade
from trading import (
    KOLBuyEvent,
    KOLContext,
    KOLCopyTradeConfig,
    TokenInput,
)
from trading.schemas import ContractData, HolderData, MarketData, WalletIntel
from zetryn.core import State
from zetryn.knowledge import KnowledgePack

# -- helpers ---------------------------------------------------------------


def _pack(tmp_path: Path, wallets: dict, **globals_) -> KnowledgePack:
    p = tmp_path / "data" / "kol_whitelist.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"wallets": wallets, **globals_}), encoding="utf-8")
    return KnowledgePack.from_dir(tmp_path)


def _token(**kw) -> TokenInput:
    defaults = dict(
        is_dangerous=False, liquidity=10_000, volume=8_000,
        top10=0.15, bundlers=0, snipers=0,
    )
    defaults.update(kw)
    return TokenInput(
        mint="M", symbol="MEME", name="Meme",
        market=MarketData(liquidity_usd=defaults["liquidity"], volume_1h=defaults["volume"]),
        holders=HolderData(top10_pct=defaults["top10"]),
        contract=ContractData(is_honeypot=defaults["is_dangerous"]),
        wallets=WalletIntel(
            bundler_wallet_count=defaults["bundlers"],
            sniper_wallet_count=defaults["snipers"],
        ),
    )


def _ctx(
    wallet: str = "ABC", sol: float = 1.0, age: float = 5.0,
    ts: float = 1000.0, last_copy: float | None = None,
    token: TokenInput | None = None,
    config: KOLCopyTradeConfig | None = None,
) -> KOLContext:
    return KOLContext(
        event=KOLBuyEvent(
            wallet=wallet, mint="M", sol_amount=sol,
            detected_at_ts=ts, block_age_seconds=age,
        ),
        token=token or _token(),
        config=config or KOLCopyTradeConfig(),
        last_copy_ts=last_copy,
    )


# -- builder validation ----------------------------------------------------


def test_builder_requires_pack_or_registry():
    with pytest.raises(ValueError):
        build_kol_copytrade()


def test_builder_accepts_empty_pack_gracefully(tmp_path):
    """No whitelist → graph still compiles; runs reject with skip."""
    empty_pack = KnowledgePack.from_dir(tmp_path)
    g = build_kol_copytrade(empty_pack)
    assert g is not None


# -- end-to-end happy path -------------------------------------------------


@pytest.mark.asyncio
async def test_healthy_kol_signal_produces_buy(tmp_path):
    pack = _pack(
        tmp_path,
        wallets={"ABC": {"name": "smart_money", "hit_rate": 0.55, "tier": "S"}},
        min_hit_rate=0.4,
    )
    g = build_kol_copytrade(pack)
    state = await g.run(State(context=_ctx()))
    d = state.output

    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    assert d.confidence > 0.5
    assert any("smart_money" in r for r in d.reasons)
    # full trace path: 4 nodes ran in order
    assert [t.node for t in state.trace] == [
        "fast_safety", "kol_quality", "fast_market", "sizing",
    ]


# -- rejection paths --------------------------------------------------------


@pytest.mark.asyncio
async def test_dangerous_contract_aborts_immediately(tmp_path):
    pack = _pack(tmp_path, wallets={"ABC": {"hit_rate": 0.55, "tier": "S"}})
    g = build_kol_copytrade(pack)
    state = await g.run(State(context=_ctx(token=_token(is_dangerous=True))))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True
    # short-circuited after fast_safety — no later nodes ran
    nodes = [t.node for t in state.trace]
    assert nodes == ["fast_safety"]


@pytest.mark.asyncio
async def test_unknown_wallet_skipped(tmp_path):
    pack = _pack(tmp_path, wallets={"ABC": {"hit_rate": 0.55, "tier": "S"}})
    g = build_kol_copytrade(pack)
    state = await g.run(State(context=_ctx(wallet="ZZZ")))
    assert state.output.action == "skip"
    assert "unknown KOL" in state.output.reasons[0]
    nodes = [t.node for t in state.trace]
    assert nodes == ["fast_safety", "kol_quality"]


@pytest.mark.asyncio
async def test_thin_liquidity_skipped(tmp_path):
    pack = _pack(tmp_path, wallets={"ABC": {"hit_rate": 0.55, "tier": "S"}})
    g = build_kol_copytrade(pack)
    state = await g.run(State(context=_ctx(token=_token(liquidity=100))))
    assert state.output.action == "skip"
    assert "liquidity" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_stale_signal_skipped(tmp_path):
    pack = _pack(tmp_path, wallets={"ABC": {"hit_rate": 0.55, "tier": "S"}})
    g = build_kol_copytrade(pack)
    state = await g.run(State(context=_ctx(age=120)))
    assert state.output.action == "skip"
    assert "too stale" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_cooldown_skips_repeat_copy(tmp_path):
    pack = _pack(tmp_path, wallets={"ABC": {"hit_rate": 0.55, "tier": "S"}})
    g = build_kol_copytrade(pack)
    state = await g.run(State(context=_ctx(ts=1010, last_copy=1000)))
    assert state.output.action == "skip"
    assert "cooldown" in state.output.reasons[0]


@pytest.mark.asyncio
async def test_below_deployment_min_hit_rate_skipped(tmp_path):
    pack = _pack(tmp_path, wallets={"ABC": {"hit_rate": 0.42, "tier": "S"}})
    g = build_kol_copytrade(pack)
    cfg = KOLCopyTradeConfig(min_kol_hit_rate=0.50)
    state = await g.run(State(context=_ctx(config=cfg)))
    assert state.output.action == "skip"
    assert "hit_rate" in state.output.reasons[0]


# -- registry pass-through vs derived-from-pack ----------------------------


@pytest.mark.asyncio
async def test_explicit_registry_overrides_pack(tmp_path):
    """Caller can pre-build a registry (e.g. assembled from multiple sources)."""
    pack = _pack(tmp_path, wallets={"OTHER": {"hit_rate": 0.6, "tier": "S"}})
    # Build registry from a different source
    custom = KOLRegistry({
        "ABC": __import__("trading").KOLProfile(hit_rate=0.65, tier="S"),
    })
    g = build_kol_copytrade(pack, registry=custom)
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"  # uses custom registry, not pack's
