"""K6 tests — KOL copy-trade `audit` mode.

The audit-mode graph runs rule sizing first (sub-ms decide returned to
the bot immediately), then fires an async LLM audit task. The bot can
await the task later and write the verdict to DecisionLog for offline
tuning. The hot path is never blocked.

Tests assert:
  - Rule sizing completes BEFORE the audit task is dispatched.
  - state.output is set and contains action="buy" with rule-derived size
    (no LLM influence on size; verdict is purely informational).
  - state.scratch["kol_audit_task"] is an awaitable.
  - The verdict is a parsed KOLAnalystVerdict (or a flagged failure
    verdict if the LLM blew up).
  - Hard-gate rejects skip the audit entirely (no wasted LLM call).
  - Builder validation rejects audit mode without an llm_client.
"""

from __future__ import annotations

import asyncio
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
            "ABC": {
                "name": "smart_money", "hit_rate": 0.55, "tier": "S",
                "exit_pattern": "scales_out_50pct",
            },
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
    """Scriptable LLMClient stand-in (same shape as confirmed-mode tests)."""

    def __init__(self, *, payload: str | None = None, raise_exc: Exception | None = None):
        self._payload = payload
        self._raise = raise_exc
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
        if self._raise is not None:
            raise self._raise
        return LLMResult(text=self._payload or "", model="fake", latency_ms=1.0)

    async def aclose(self) -> None:
        self.closed = True


def _audit_payload(approve: bool = True, *, confidence: float = 0.8) -> str:
    return json.dumps({
        "approve": approve,
        "size_multiplier": 1.0,
        "confidence": confidence,
        "concerns": [] if approve else ["disagree with rule sizing"],
        "reasoning": "agrees with rule decision" if approve else "would size smaller",
    })


# -- builder validation ----------------------------------------------------


def test_audit_mode_requires_llm_client(tmp_path):
    with pytest.raises(ValueError, match="llm_client"):
        build_kol_copytrade(_pack(tmp_path), mode="audit")


def test_invalid_mode_still_rejected(tmp_path):
    with pytest.raises(ValueError, match="unsupported mode"):
        build_kol_copytrade(_pack(tmp_path), mode="bogus")


# -- core audit-mode behaviour --------------------------------------------


@pytest.mark.asyncio
async def test_audit_mode_returns_rule_decision_immediately(tmp_path):
    """Decision is set BEFORE the audit task completes (sub-ms latency)."""
    llm = _ScriptedLLM(payload=_audit_payload())
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    d = state.output
    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    # Rule sizing wasn't influenced by the analyst — confirmed-mode multiplier
    # would have shown up in scores; audit mode never sets it.
    assert "analyst_size_multiplier" not in d.scores
    # The audit task exists in scratch — bot can await it later.
    assert "kol_audit_task" in state.scratch
    assert isinstance(state.scratch["kol_audit_task"], asyncio.Task)
    # Decision is flagged so observers know audit is in flight.
    assert d.flags.get("kol_audit_dispatched") is True


@pytest.mark.asyncio
async def test_audit_task_resolves_to_verdict(tmp_path):
    """Awaiting the task returns a parsed KOLAnalystVerdict."""
    llm = _ScriptedLLM(payload=_audit_payload(approve=True, confidence=0.9))
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    verdict = await state.scratch["kol_audit_task"]
    assert isinstance(verdict, KOLAnalystVerdict)
    assert verdict.approve is True
    assert verdict.confidence == 0.9


@pytest.mark.asyncio
async def test_audit_task_disagrees_does_not_change_decision(tmp_path):
    """An approve=False verdict is informational only — bot already traded."""
    llm = _ScriptedLLM(payload=_audit_payload(approve=False))
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    # The buy decision is unchanged
    assert state.output.action == "buy"
    assert state.output.size is not None and state.output.size > 0
    # But the audit verdict can be inspected after the fact
    verdict = await state.scratch["kol_audit_task"]
    assert verdict.approve is False
    assert "disagree" in verdict.concerns[0] or "size smaller" in verdict.reasoning


@pytest.mark.asyncio
async def test_audit_task_swallows_llm_failure_into_flagged_verdict(tmp_path):
    """LLM error becomes a verdict with audit_failed concern — never raises."""
    llm = _ScriptedLLM(raise_exc=LLMError("provider down"))
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)
    state = await g.run(State(context=_ctx()))

    # Decision still went through — failure is isolated to the bg task.
    assert state.output.action == "buy"
    verdict = await state.scratch["kol_audit_task"]
    assert verdict.approve is False
    assert any("audit_failed" in c for c in verdict.concerns)


@pytest.mark.asyncio
async def test_audit_task_swallows_garbage_json(tmp_path):
    """Non-JSON / invalid schema also becomes a flagged verdict."""
    llm = _ScriptedLLM(payload="this is not json")
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)
    state = await g.run(State(context=_ctx()))
    verdict = await state.scratch["kol_audit_task"]
    assert any("audit_failed" in c for c in verdict.concerns)


# -- short-circuit paths ---------------------------------------------------


@pytest.mark.asyncio
async def test_audit_does_not_run_on_hard_gate_reject(tmp_path):
    """Honeypot → fast_safety abort. No audit task should be dispatched."""
    llm = _ScriptedLLM(payload=_audit_payload())
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)

    ctx = _ctx()
    ctx.token.contract.is_honeypot = True
    state = await g.run(State(context=ctx))

    assert state.output.action == "abort"
    assert llm.calls == 0  # LLM never called
    assert "kol_audit_task" not in state.scratch
    # Trace should also confirm
    assert "kol_audit_dispatch" not in [t.node for t in state.trace]


@pytest.mark.asyncio
async def test_audit_does_not_run_on_kol_quality_skip(tmp_path):
    """Unknown KOL → kol_quality skip. No audit task should be dispatched."""
    llm = _ScriptedLLM(payload=_audit_payload())
    g = build_kol_copytrade(_pack(tmp_path), mode="audit", llm_client=llm)

    ctx = _ctx()
    ctx.event.wallet = "UNKNOWN"
    state = await g.run(State(context=ctx))

    assert state.output.action == "skip"
    assert llm.calls == 0
    assert "kol_audit_task" not in state.scratch


# -- backwards compat -----------------------------------------------------


@pytest.mark.asyncio
async def test_rule_mode_unchanged_after_audit_landed(tmp_path):
    """v0.6.0 rule-mode users should see zero behaviour change."""
    g = build_kol_copytrade(_pack(tmp_path))   # mode="rule" default
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    assert "kol_audit_task" not in state.scratch


@pytest.mark.asyncio
async def test_confirmed_mode_unchanged_after_audit_landed(tmp_path):
    """v0.7.0 confirmed-mode users should also see zero change."""
    llm = _ScriptedLLM(payload=json.dumps({
        "approve": True, "size_multiplier": 1.0, "confidence": 0.7,
        "concerns": [], "reasoning": "OK",
    }))
    g = build_kol_copytrade(_pack(tmp_path), mode="confirmed", llm_client=llm)
    state = await g.run(State(context=_ctx()))
    # Confirmed mode still influences SIZE — not an audit dispatch.
    assert state.output.action == "buy"
    assert "analyst_size_multiplier" in state.output.scores
    assert "kol_audit_task" not in state.scratch
