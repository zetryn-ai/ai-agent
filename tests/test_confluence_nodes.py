"""Tests for Smart Money Confluence rule nodes (v0.14.0 / S5)."""

from __future__ import annotations


from strategies import SAMPLE_TOKENS, SmartWalletRegistry, build_confluence
from trading import (
    ConfluenceConfig,
    ConfluenceContext,
    ConfluenceEvent,
    SmartWalletAccumulation,
    SmartWalletProfile,
)
from zetryn.core import State

_NOW = 1_700_000_000.0
_WALLETS = {
    "wallet_A": SmartWalletProfile(hit_rate=0.6, avg_pnl_pct=1.2, trades_30d=50, tier="A"),
    "wallet_B": SmartWalletProfile(hit_rate=0.55, avg_pnl_pct=0.9, trades_30d=40, tier="A"),
    "wallet_C": SmartWalletProfile(hit_rate=0.5, avg_pnl_pct=0.7, trades_30d=30, tier="B"),
    "wallet_D": SmartWalletProfile(hit_rate=0.45, avg_pnl_pct=0.5, trades_30d=25, tier="B"),
    "wallet_E": SmartWalletProfile(hit_rate=0.4, avg_pnl_pct=0.4, trades_30d=20, tier="B"),
}
_REGISTRY = SmartWalletRegistry(_WALLETS, min_tier="B", min_hit_rate=0.35)


def _acc(wallet: str, sol: float = 1.0, age: float = 5.0) -> SmartWalletAccumulation:
    return SmartWalletAccumulation(
        wallet=wallet,
        mint="MINT_X",
        sol_amount=sol,
        detected_at_ts=_NOW,
        block_age_seconds=age,
    )


def _event(wallets: list[str] | None = None, **over) -> ConfluenceEvent:
    accs = [_acc(w) for w in (wallets or list(_WALLETS.keys()))]
    base = dict(
        mint="MINT_X",
        detected_at_ts=_NOW,
        window_seconds=7 * 24 * 3600,
        accumulations=accs,
    )
    base.update(over)
    return ConfluenceEvent(**base)


def _ctx(event=None, token=None, **cfg) -> ConfluenceContext:
    return ConfluenceContext(
        token=token if token is not None else SAMPLE_TOKENS["GOOD"],
        event=event if event is not None else _event(),
        config=ConfluenceConfig(**cfg),
    )


# -- fast_safety -------------------------------------------------------------


async def test_fast_safety_aborts_dangerous_contract():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx(token=SAMPLE_TOKENS["RUG"])))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True
    assert [t.node for t in state.trace] == ["fast_safety"]


# -- confluence_gate (with registry) -----------------------------------------


async def test_confluence_gate_passes_good_event():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "confluence_gate" in nodes
    assert "market_gate" in nodes
    assert "rule_buy" in nodes


async def test_confluence_gate_rejects_empty_accumulations():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    ev = ConfluenceEvent(mint="MINT_X", detected_at_ts=_NOW, window_seconds=3600, accumulations=[])
    state = await g.run(State(context=_ctx(event=ev)))
    assert state.output.action == "skip"
    assert "no accumulations" in state.output.reasons[0]


async def test_confluence_gate_rejects_stale_signal():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    # All accumulations are 120s old, max is 60s
    accs = [_acc(w, age=120.0) for w in list(_WALLETS.keys())]
    ev = ConfluenceEvent(mint="MINT_X", detected_at_ts=_NOW, window_seconds=3600, accumulations=accs)
    state = await g.run(State(context=_ctx(event=ev)))
    assert state.output.action == "skip"
    assert "old" in state.output.reasons[0]


async def test_confluence_gate_rejects_too_few_wallets():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    # Only 2 wallets, min is 5
    ev = _event(wallets=["wallet_A", "wallet_B"])
    state = await g.run(State(context=_ctx(event=ev)))
    assert state.output.action == "skip"
    assert "qualifying smart wallets" in state.output.reasons[0]


async def test_confluence_gate_rejects_unknown_wallet_when_registry_present():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    # Only 1 known wallet; 4 unknown wallets don't count
    accs = [_acc("wallet_A"), _acc("unknown_1"), _acc("unknown_2"), _acc("unknown_3"), _acc("unknown_4")]
    ev = ConfluenceEvent(mint="MINT_X", detected_at_ts=_NOW, window_seconds=3600, accumulations=accs)
    state = await g.run(State(context=_ctx(event=ev)))
    assert state.output.action == "skip"
    assert "qualifying smart wallets" in state.output.reasons[0]


async def test_confluence_gate_rejects_small_sol():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    # All wallets buy only 0.1 SOL — below min_sol_per_wallet 0.5
    accs = [_acc(w, sol=0.1) for w in list(_WALLETS.keys())]
    ev = ConfluenceEvent(mint="MINT_X", detected_at_ts=_NOW, window_seconds=3600, accumulations=accs)
    state = await g.run(State(context=_ctx(event=ev)))
    assert state.output.action == "skip"
    assert "qualifying smart wallets" in state.output.reasons[0]


async def test_confluence_gate_no_registry_uses_config_floors():
    # Without a registry, gate uses config min_hit_rate/min_tier floors
    # Falls back to "all wallets count" since we can't verify individually
    g = build_confluence(llm_client=None, registry=None)
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"


async def test_confluence_gate_deduplicates_same_wallet():
    # Same wallet appearing twice should only count once
    accs = [_acc("wallet_A"), _acc("wallet_A"), _acc("wallet_B"), _acc("wallet_C"), _acc("wallet_D"), _acc("wallet_E")]
    ev = ConfluenceEvent(mint="MINT_X", detected_at_ts=_NOW, window_seconds=3600, accumulations=accs)
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx(event=ev)))
    # wallet_A deduped → still 5 unique qualifying wallets → buy
    assert state.output.action == "buy"
    assert state.scratch["unique_wallet_count"] == 5


# -- market_gate -------------------------------------------------------------


async def test_market_gate_rejects_low_liquidity():
    token = SAMPLE_TOKENS["GOOD"].model_copy(
        update={"market": SAMPLE_TOKENS["GOOD"].market.model_copy(update={"liquidity_usd": 100.0})}
    )
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx(token=token)))
    assert state.output.action == "skip"
    assert "liquidity" in state.output.reasons[0]


async def test_market_gate_rejects_high_top10():
    token = SAMPLE_TOKENS["GOOD"].model_copy(
        update={"holders": SAMPLE_TOKENS["GOOD"].holders.model_copy(update={"top10_pct": 0.9})}
    )
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx(token=token)))
    assert state.output.action == "skip"
    assert "top10_pct" in state.output.reasons[0]


# -- rule_size_and_buy -------------------------------------------------------


async def test_rule_buy_size_scales_with_wallet_count():
    g5 = build_confluence(llm_client=None, registry=_REGISTRY)
    # Add 5 more wallets beyond the 5 minimum → max wallet_mult = 2.0
    extra_wallets = {
        f"wallet_extra_{i}": SmartWalletProfile(hit_rate=0.5, tier="B")
        for i in range(5)
    }
    big_registry = SmartWalletRegistry(
        {**_WALLETS, **extra_wallets}, min_tier="B", min_hit_rate=0.35
    )
    g10 = build_confluence(llm_client=None, registry=big_registry)

    ev5 = _event()  # 5 wallets
    ev10 = _event(wallets=list(_WALLETS.keys()) + list(extra_wallets.keys()))

    s5 = await g5.run(State(context=_ctx(event=ev5)))
    s10 = await g10.run(State(context=ConfluenceContext(
        token=SAMPLE_TOKENS["GOOD"],
        event=ev10,
        config=ConfluenceConfig(),
    )))
    # More wallets → larger size
    assert s10.output.size > s5.output.size


async def test_rule_buy_confidence_is_bounded():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx()))
    d = state.output
    assert 0.0 <= d.confidence <= 1.0
    assert d.size is not None and 0.0 < d.size <= ConfluenceConfig().max_size


async def test_full_trace_order_rule_mode():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx()))
    assert [t.node for t in state.trace] == [
        "fast_safety", "confluence_gate", "market_gate", "rule_buy"
    ]
