"""K5 tests — KOL copy-trade `confirmed` mode (LLM analyst before sizing).

Uses scripted fake LLM clients so the tests are deterministic and offline.
The analyst LLM in confirmed mode can:
  - approve with size_multiplier 1.0 → trade goes through at rule size
  - approve with size_multiplier < 1.0 → trade goes through at reduced size
  - approve with size_multiplier > 1.0 → trade goes through at boosted size
  - veto (approve=False) → action becomes "skip" even though rules said buy
  - fail entirely → neutral_kol_verdict fallback (deferred to rule decision)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from strategies import build_kol_copytrade
from trading import (
    KOLAnalystVerdict,
    KOLBuyEvent,
    KOLContext,
    KOLCopyTradeConfig,
    TokenInput,
)
from trading.schemas import ContractData, HolderData, MarketData, WalletIntel
from zetryn.core import State
from zetryn.knowledge import KnowledgePack
from zetryn.llm.types import LLMError, LLMResult, Message

# -- fixtures --------------------------------------------------------------


def _pack(tmp_path: Path) -> KnowledgePack:
    data = tmp_path / "data" / "kol_whitelist.json"
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps({
        "wallets": {
            "ABC": {"name": "smart_money", "hit_rate": 0.55, "tier": "S",
                    "exit_pattern": "scales_out_50pct"},
        },
        "min_hit_rate": 0.40,
    }), encoding="utf-8")
    return KnowledgePack.from_dir(tmp_path)


def _ctx() -> KOLContext:
    return KOLContext(
        event=KOLBuyEvent(
            wallet="ABC", mint="M", sol_amount=1.5,
            detected_at_ts=1000.0, block_age_seconds=4.0,
        ),
        token=TokenInput(
            mint="M", symbol="MEME", name="Meme",
            market=MarketData(liquidity_usd=10_000, volume_1h=8_000),
            holders=HolderData(top10_pct=0.18),
            contract=ContractData(),
            wallets=WalletIntel(bundler_wallet_count=0, sniper_wallet_count=2),
        ),
        config=KOLCopyTradeConfig(),
    )


class _ScriptedLLM:
    """Returns one canned text per call (stand-in for OpenAICompatibleClient)."""

    def __init__(self, *, payload: str | None = None, raise_exc: Exception | None = None):
        self._payload = payload
        self._raise = raise_exc
        self.calls = 0
        self.received_messages: list[list[Message]] = []
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
        self.received_messages.append(messages)
        if self._raise is not None:
            raise self._raise
        return LLMResult(text=self._payload or "", model="fake", latency_ms=1.0)

    async def aclose(self) -> None:
        self.closed = True


def _verdict_payload(**kw) -> str:
    base = {
        "approve": True,
        "size_multiplier": 1.0,
        "confidence": 0.7,
        "concerns": [],
        "reasoning": "Looks fine.",
    }
    base.update(kw)
    return json.dumps(base)


# -- builder validation ----------------------------------------------------


def test_confirmed_mode_requires_llm_client(tmp_path):
    pack = _pack(tmp_path)
    with pytest.raises(ValueError, match="llm_client"):
        build_kol_copytrade(pack, mode="confirmed")


def test_invalid_mode_rejected(tmp_path):
    pack = _pack(tmp_path)
    with pytest.raises(ValueError, match="unsupported mode"):
        build_kol_copytrade(pack, mode="bogus")


# -- happy path ------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_mode_full_approve_keeps_rule_size(tmp_path):
    """Analyst approves at multiplier=1.0 → final size = rule size."""
    pack = _pack(tmp_path)
    llm = _ScriptedLLM(payload=_verdict_payload(size_multiplier=1.0, confidence=0.8))
    g = build_kol_copytrade(pack, mode="confirmed", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    d = state.output
    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    # Analyst was actually called
    assert llm.calls == 1
    # The verdict is in scratch and surfaced into reasons
    assert isinstance(state.scratch["kol_analyst"], KOLAnalystVerdict)
    assert any("analyst" in r.lower() for r in d.reasons)
    # Trace includes the analyst node
    assert "kol_analyst" in [t.node for t in state.trace]


@pytest.mark.asyncio
async def test_confirmed_mode_half_size_multiplier_reduces_size(tmp_path):
    """multiplier=0.5 cuts the rule size in half."""
    pack = _pack(tmp_path)
    rule_llm = _ScriptedLLM(payload=_verdict_payload(size_multiplier=1.0))
    half_llm = _ScriptedLLM(payload=_verdict_payload(size_multiplier=0.5))

    g_full = build_kol_copytrade(pack, mode="confirmed", llm_client=rule_llm)
    g_half = build_kol_copytrade(pack, mode="confirmed", llm_client=half_llm)

    full_state = await g_full.run(State(context=_ctx()))
    half_state = await g_half.run(State(context=_ctx()))

    assert half_state.output.size == pytest.approx(full_state.output.size / 2, rel=1e-3)


@pytest.mark.asyncio
async def test_confirmed_mode_boost_size_multiplier(tmp_path):
    """multiplier=1.5 boosts above rule size (still clamped at max_size)."""
    pack = _pack(tmp_path)
    cfg = KOLCopyTradeConfig(base_size=1.0, max_size=10.0)  # generous cap
    llm = _ScriptedLLM(payload=_verdict_payload(size_multiplier=1.5))
    g = build_kol_copytrade(pack, mode="confirmed", llm_client=llm)

    ctx = _ctx()
    ctx.config = cfg
    state = await g.run(State(context=ctx))
    # Rule kol_mult ~2.0 at hit_rate 0.55 (floor 0.4, ceil 0.7, conf=0.5)
    # top10=0.18, no penalty (penalty_start=0.20) → top10_pen ~1.0
    # rule_size = 1.0 * 2.0 * 1.0 = 2.0
    # final = 2.0 * 1.5 = 3.0
    assert state.output.size == pytest.approx(3.0, abs=0.05)


# -- veto path ------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_mode_veto_skips_the_trade(tmp_path):
    """approve=False → action becomes 'skip' even though rules approved."""
    pack = _pack(tmp_path)
    llm = _ScriptedLLM(payload=_verdict_payload(
        approve=False, confidence=0.85,
        concerns=["kol exit_pattern is dump_followers"],
        reasoning="KOL has historic followers-dump exit; passing on this one.",
    ))
    g = build_kol_copytrade(pack, mode="confirmed", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    d = state.output
    assert d.action == "skip"
    assert d.size is None
    assert d.flags.get("analyst_veto") is True
    assert any("dump_followers" in r for r in d.reasons)
    assert any("analyst veto" in r for r in d.reasons)


# -- failure path ---------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_mode_falls_back_when_llm_dies(tmp_path):
    """LLM error → neutral_kol_verdict fallback (approve True, mult 1.0)."""
    pack = _pack(tmp_path)
    llm = _ScriptedLLM(raise_exc=LLMError("provider down"))
    g = build_kol_copytrade(pack, mode="confirmed", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    d = state.output
    # Falls back to rule decision (buy with rule size).
    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    # llm_failed flag surfaced; no analyst veto
    assert d.flags["llm_failed"] is True
    assert "analyst_veto" not in d.flags or d.flags["analyst_veto"] is False
    # Neutral verdict still recorded
    assert isinstance(state.scratch["kol_analyst"], KOLAnalystVerdict)
    assert state.scratch["kol_analyst"].approve is True


@pytest.mark.asyncio
async def test_confirmed_mode_falls_back_when_llm_returns_garbage(tmp_path):
    """Non-JSON or schema-invalid output → fallback after retries."""
    pack = _pack(tmp_path)
    llm = _ScriptedLLM(payload="this is not json at all")
    g = build_kol_copytrade(pack, mode="confirmed", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    d = state.output
    # Fallback ran; trade defers to rule decision
    assert d.action == "buy"
    assert d.flags["llm_failed"] is True


# -- rule mode still works unchanged --------------------------------------


@pytest.mark.asyncio
async def test_rule_mode_does_not_call_llm(tmp_path):
    """Backwards-compat: rule mode (default) must not require or call an LLM."""
    pack = _pack(tmp_path)
    llm = _ScriptedLLM(payload=_verdict_payload())  # would be used if called
    # Note: passing llm_client in rule mode is silently fine — it's just unused.
    g = build_kol_copytrade(pack)  # default mode="rule"
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    assert llm.calls == 0  # never called
    assert "kol_analyst" not in [t.node for t in state.trace]


@pytest.mark.asyncio
async def test_confirmed_mode_respects_hard_gate_short_circuit(tmp_path):
    """Hard-gate rejects still short-circuit BEFORE the analyst is called."""
    pack = _pack(tmp_path)
    llm = _ScriptedLLM(payload=_verdict_payload())
    g = build_kol_copytrade(pack, mode="confirmed", llm_client=llm)

    # Honeypot — should reject at fast_safety
    ctx = _ctx()
    ctx.token.contract.is_honeypot = True
    state = await g.run(State(context=ctx))

    assert state.output.action == "abort"
    assert llm.calls == 0  # analyst never ran — money saved
    assert "kol_analyst" not in [t.node for t in state.trace]
