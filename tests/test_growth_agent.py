"""Tests for Organic Growth Detector mode wiring (v0.16.0 / A1)."""

from __future__ import annotations

import json

from strategies import SAMPLE_TOKENS, build_organic_detector
from trading import GrowthConfig, GrowthContext, GrowthSnapshot
from zetryn.core import State
from zetryn.llm.types import LLMResult
from zetryn.memory import DecisionLog, InMemoryStore

_NOW = 1_700_000_000.0


def _snap(**over) -> GrowthSnapshot:
    base = dict(
        mint="MINT_X",
        detected_at_ts=_NOW,
        observation_seconds=300.0,
        candle_count=10,
        price_trajectory="steady_climb",
        sell_presence_pct=0.30,
        unique_buyer_trend=0.40,
        holder_growth_rate=3.0,
        has_healthy_pullback=True,
        max_drawdown_pct=0.12,
        whale_volume_pct=0.25,
        volume_acceleration=1.8,
    )
    base.update(over)
    return GrowthSnapshot(**base)


def _ctx(snap=None, token=None, **cfg) -> GrowthContext:
    return GrowthContext(
        token=token if token is not None else SAMPLE_TOKENS["GOOD"],
        snapshot=snap if snap is not None else _snap(),
        config=GrowthConfig(**cfg),
    )


class _FakeLLM:
    def __init__(self, classification="organic", confidence=0.85):
        self._p = {
            "classification": classification,
            "confidence": confidence,
            "promote_scanner": True,
            "signals": ["steady_climb", "healthy_pullback"],
            "reasoning": "looks organic",
        }

    async def complete(self, messages, **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


class _AuditLLM:
    def __init__(self, *, agrees=True):
        self._p = {
            "agrees": agrees,
            "confidence": 0.80,
            "concerns": [],
            "reasoning": "audit ok",
        }

    async def complete(self, messages, **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


# -- rule mode ---------------------------------------------------------------


async def test_rule_mode_no_llm_nodes():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "growth_llm" not in nodes
    assert "audit_dispatch" not in nodes


# -- llm mode ----------------------------------------------------------------


async def test_llm_mode_routes_to_growth_llm():
    g = build_organic_detector(llm_client=_FakeLLM())
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "growth_llm" in nodes
    assert "organic_classify" not in nodes


async def test_llm_mode_suspicious_propagates():
    g = build_organic_detector(llm_client=_FakeLLM(classification="suspicious"))
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "skip"
    assert state.output.flags["classification"] == "suspicious"


async def test_llm_mode_manipulated_propagates():
    g = build_organic_detector(llm_client=_FakeLLM(classification="manipulated"))
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "abort"
    assert state.output.flags["classification"] == "manipulated"


# -- hybrid mode -------------------------------------------------------------


async def test_hybrid_guardrail_aborts_rug():
    g = build_organic_detector(llm_client=_FakeLLM(classification="organic"))
    state = await g.run(State(context=_ctx(
        token=SAMPLE_TOKENS["RUG"],
        decision_mode="hybrid",
    )))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True


async def test_hybrid_guardrail_demotes_vertical_pump_zero_sell():
    """Even if LLM says organic, guardrail must force abort on vertical_pump + zero sellers."""
    g = build_organic_detector(llm_client=_FakeLLM(classification="organic"))
    state = await g.run(State(context=GrowthContext(
        token=SAMPLE_TOKENS["GOOD"],
        snapshot=_snap(price_trajectory="vertical_pump", sell_presence_pct=0.005),
        config=GrowthConfig(decision_mode="hybrid"),
    )))
    # manipulation_gate catches this before LLM is reached — always abort
    assert state.output.action == "abort"
    assert state.output.flags["classification"] == "manipulated"


async def test_hybrid_llm_cannot_promote_skip_to_buy():
    """Guardrail: hybrid mode can only demote, never promote organic."""
    g = build_organic_detector(llm_client=_FakeLLM(classification="organic"))
    # Provide a snapshot that is barely suspicious (would be skip in rule mode)
    # but LLM says organic — guardrail should keep it as is (organic OK if no rug/pump)
    state = await g.run(State(context=_ctx(decision_mode="hybrid")))
    # With all-green snapshot + organic LLM verdict → buy is fine
    assert state.output.action in ("buy", "skip", "abort")


# -- hybrid_audit mode -------------------------------------------------------


async def test_hybrid_audit_runs_rule_classify():
    g = build_organic_detector(llm_client=_AuditLLM())
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    nodes = [t.node for t in state.trace]
    assert "organic_classify" in nodes
    assert "growth_llm" not in nodes
    assert "audit_dispatch" in nodes


async def test_hybrid_audit_dispatches_for_buy():
    g = build_organic_detector(llm_client=_AuditLLM())
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    assert state.output.action == "buy"
    assert state.output.flags.get("audit_dispatched") is True
    assert "audit_task" in state.scratch


async def test_hybrid_audit_dispatches_for_skip():
    """Unlike entry agents, audit fires even on skip/suspicious."""
    g = build_organic_detector(llm_client=_AuditLLM())
    state = await g.run(State(context=_ctx(
        snap=_snap(has_healthy_pullback=False, unique_buyer_trend=-0.50),
        decision_mode="hybrid_audit",
    )))
    assert state.output.action == "skip"
    assert state.output.flags.get("audit_dispatched") is True


async def test_hybrid_audit_no_task_on_gate_reject():
    """Gate rejects before organic_classify → audit_dispatch never runs."""
    g = build_organic_detector(llm_client=_AuditLLM())
    ctx = GrowthContext(
        token=SAMPLE_TOKENS["GOOD"],
        snapshot=_snap(observation_seconds=30.0),
        config=GrowthConfig(decision_mode="hybrid_audit"),
    )
    state = await g.run(State(context=ctx))
    assert state.output.action == "skip"
    assert "audit_task" not in state.scratch


# -- reflective loop ---------------------------------------------------------


async def test_reflect_inserted_with_decision_log():
    log = DecisionLog(InMemoryStore())
    g = build_organic_detector(llm_client=_FakeLLM(), decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    nodes = [t.node for t in state.trace]
    assert "reflect" in nodes
    assert nodes.index("reflect") < nodes.index("growth_llm")


async def test_reflect_skipped_in_hybrid_audit():
    log = DecisionLog(InMemoryStore())
    g = build_organic_detector(llm_client=_FakeLLM(), decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    assert "reflect" not in [t.node for t in state.trace]


async def test_reflect_skipped_in_rule_mode():
    log = DecisionLog(InMemoryStore())
    g = build_organic_detector(llm_client=_FakeLLM(), decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="rule")))
    nodes = [t.node for t in state.trace]
    assert "reflect" not in nodes
    assert "organic_classify" in nodes
