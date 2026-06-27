"""Graduation × ReflectiveNode integration tests (v0.12.0)."""

from __future__ import annotations

import json

from strategies import SAMPLE_TOKENS, build_graduation
from trading import GraduationConfig, GraduationContext, GraduationEvent
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message
from zetryn.memory import DecisionLog, InMemoryStore


def _event() -> GraduationEvent:
    return GraduationEvent(
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


def _ctx(**cfg) -> GraduationContext:
    return GraduationContext(
        token=SAMPLE_TOKENS["GOOD"],
        event=_event(),
        config=GraduationConfig(**cfg),
    )


class _CapturingLLM:
    def __init__(self) -> None:
        self.received_messages: list[list[Message]] = []
        self._payload = json.dumps({
            "action": "buy",
            "size_pct": 0.5,
            "confidence": 0.8,
            "reasoning": "ok",
            "concerns": [],
        })

    async def complete(self, messages, **kw) -> LLMResult:
        self.received_messages.append(messages)
        return LLMResult(text=self._payload, model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


async def _seed_losers(log: DecisionLog) -> None:
    for i, (mint, pnl) in enumerate([
        ("LOSER1", -0.25),
        ("LOSER2", -0.30),
        ("LOSER3", -0.18),
    ]):
        run_id = f"loss-{i}"
        await log.log(run_id, {"mint": mint, "top10_pct": 0.35, "action": "buy"})
        await log.record_outcome(run_id, {"pnl": pnl})


# -- llm / hybrid: reflection wired in ---------------------------------------


async def test_seeded_losers_lessons_reach_llm_prompt():
    log = DecisionLog(InMemoryStore())
    await _seed_losers(log)
    llm = _CapturingLLM()
    g = build_graduation(llm, decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="hybrid")))

    assert state.output.action == "buy"
    assert "lessons_text" in state.scratch
    assert "lessons" in state.scratch

    assert len(llm.received_messages) == 1
    system_msgs = [
        m["content"] for m in llm.received_messages[0] if m["role"] == "system"
    ]
    lessons = [c for c in system_msgs if "LESSONS from recent graduation snipe" in c]
    assert len(lessons) == 1


async def test_empty_log_runs_reflect_no_lessons_block_breaks_anything():
    log = DecisionLog(InMemoryStore())
    llm = _CapturingLLM()
    g = build_graduation(llm, decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert "reflect" in [t.node for t in state.trace]
    assert "lessons_text" in state.scratch
    assert state.output.action == "buy"


async def test_reflect_window_parameter_threading():
    log = DecisionLog(InMemoryStore())
    await _seed_losers(log)
    g = build_graduation(_CapturingLLM(), decision_log=log, reflect_window=3)
    reflect_node = g._nodes["reflect"]  # type: ignore[attr-defined]
    assert reflect_node._window == 3  # type: ignore[attr-defined]


# -- rule / hybrid_audit modes skip reflect ----------------------------------


async def test_rule_mode_skips_reflect_even_with_log():
    log = DecisionLog(InMemoryStore())
    await _seed_losers(log)
    g = build_graduation(_CapturingLLM(), decision_log=log)
    state = await g.run(State(context=_ctx()))  # default rule
    nodes = [t.node for t in state.trace]
    assert "reflect" not in nodes
    assert state.output.action == "buy"


async def test_hybrid_audit_skips_reflect_to_preserve_subms_path():
    log = DecisionLog(InMemoryStore())
    await _seed_losers(log)
    g = build_graduation(_CapturingLLM(), decision_log=log)
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    nodes = [t.node for t in state.trace]
    assert "reflect" not in nodes
    assert "rule_buy" in nodes
    assert "audit_dispatch" in nodes


async def test_no_llm_client_with_log_short_circuits_reflect():
    log = DecisionLog(InMemoryStore())
    await _seed_losers(log)
    g = build_graduation(llm_client=None, decision_log=log)
    state = await g.run(State(context=_ctx()))
    nodes = [t.node for t in state.trace]
    assert "reflect" not in nodes
    assert "grad_decide" not in nodes
    assert state.output.action == "buy"
