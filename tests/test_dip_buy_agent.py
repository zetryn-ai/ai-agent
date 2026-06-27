"""Tests for Early-Stage Dip Buy mode wiring (v0.15.0 / S6)."""

from __future__ import annotations

import json

from strategies import SAMPLE_TOKENS, build_dip_buy
from trading import DipBuyConfig, DipBuyContext, DipBuySnapshot
from zetryn.core import State
from zetryn.llm.types import LLMResult
from zetryn.memory import DecisionLog, InMemoryStore

_NOW = 1_700_000_000.0


def _snap(**over) -> DipBuySnapshot:
    base = dict(
        event_type="launch",
        mint="MINT_X",
        detected_at_ts=_NOW,
        time_since_event_seconds=180.0,
        price_vs_ath_pct=-0.30,
        sell_pressure_score=0.20,
        buy_ratio_5m=0.60,
        holder_retention_pct=0.75,
        unique_buyers_trend=0.30,
        price_stable_seconds=60.0,
    )
    base.update(over)
    return DipBuySnapshot(**base)


def _ctx(**cfg) -> DipBuyContext:
    return DipBuyContext(
        token=SAMPLE_TOKENS["GOOD"],
        snapshot=_snap(),
        config=DipBuyConfig(**cfg),
    )


class _FakeLLM:
    def __init__(self, action="buy", size_pct=0.5, confidence=0.8):
        self._p = {
            "action": action,
            "size_pct": size_pct,
            "confidence": confidence,
            "reasoning": "ok",
            "concerns": [],
        }

    async def complete(self, messages, **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


class _AuditLLM:
    def __init__(self, *, agrees=True):
        self._p = {
            "agrees": agrees,
            "confidence": 0.85,
            "concerns": [],
            "reasoning": "audit ok",
        }

    async def complete(self, messages, **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


# -- rule mode ---------------------------------------------------------------


async def test_rule_mode_no_llm_nodes():
    g = build_dip_buy()
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "dip_decide" not in nodes
    assert "audit_dispatch" not in nodes


# -- llm mode ----------------------------------------------------------------


async def test_llm_mode_routes_to_decide():
    g = build_dip_buy(llm_client=_FakeLLM())
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "dip_decide" in nodes
    assert "rule_buy" not in nodes


async def test_llm_mode_skip_propagates():
    g = build_dip_buy(llm_client=_FakeLLM(action="skip"))
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "skip"


# -- hybrid mode -------------------------------------------------------------


async def test_hybrid_guardrail_caps_size():
    g = build_dip_buy(llm_client=_FakeLLM(action="buy", size_pct=1.0))
    state = await g.run(State(context=_ctx(decision_mode="hybrid", max_size=1.5)))
    assert state.output.action == "buy"
    assert state.output.size is not None and state.output.size <= 1.5


async def test_hybrid_guardrail_aborts_rug():
    g = build_dip_buy(llm_client=_FakeLLM(action="buy"))
    state = await g.run(State(context=DipBuyContext(
        token=SAMPLE_TOKENS["RUG"],
        snapshot=_snap(),
        config=DipBuyConfig(decision_mode="hybrid"),
    )))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True


# -- hybrid_audit mode -------------------------------------------------------


async def test_hybrid_audit_dispatches_for_buy():
    g = build_dip_buy(llm_client=_AuditLLM())
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    nodes = [t.node for t in state.trace]
    assert "rule_buy" in nodes
    assert "audit_dispatch" in nodes
    assert "dip_decide" not in nodes
    assert state.output.flags.get("audit_dispatched") is True
    assert "audit_task" in state.scratch


async def test_hybrid_audit_no_task_on_gate_reject():
    g = build_dip_buy(llm_client=_AuditLLM())
    # Make timing_gate reject
    ctx = DipBuyContext(
        token=SAMPLE_TOKENS["GOOD"],
        snapshot=_snap(time_since_event_seconds=10.0),
        config=DipBuyConfig(decision_mode="hybrid_audit"),
    )
    state = await g.run(State(context=ctx))
    assert state.output.action == "skip"
    assert "audit_task" not in state.scratch


# -- reflective loop ---------------------------------------------------------


async def test_reflect_inserted_with_decision_log():
    log = DecisionLog(InMemoryStore())
    g = build_dip_buy(llm_client=_FakeLLM(), decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    nodes = [t.node for t in state.trace]
    assert "reflect" in nodes
    assert nodes.index("reflect") < nodes.index("dip_decide")


async def test_reflect_skipped_in_hybrid_audit():
    log = DecisionLog(InMemoryStore())
    g = build_dip_buy(llm_client=_FakeLLM(), decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    assert "reflect" not in [t.node for t in state.trace]


# -- event_type separation ---------------------------------------------------


async def test_graduation_event_type_passes_with_wider_window():
    g = build_dip_buy()
    ctx = DipBuyContext(
        token=SAMPLE_TOKENS["GOOD"],
        snapshot=_snap(event_type="graduation", time_since_event_seconds=900.0),
        config=DipBuyConfig(
            event_type="graduation",
            max_time_since_event_seconds=1800.0,
        ),
    )
    state = await g.run(State(context=ctx))
    assert state.output.action == "buy"


async def test_launch_event_rejects_at_900s():
    g = build_dip_buy()
    # Launch window max is 600s — 900s too late
    ctx = DipBuyContext(
        token=SAMPLE_TOKENS["GOOD"],
        snapshot=_snap(event_type="launch", time_since_event_seconds=900.0),
        config=DipBuyConfig(event_type="launch", max_time_since_event_seconds=600.0),
    )
    state = await g.run(State(context=ctx))
    assert state.output.action == "skip"
    assert "too late" in state.output.reasons[0]
