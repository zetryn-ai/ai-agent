"""Tests for M6: sniper agent (pure-rule fast path) + LLM-decide/hybrid."""

import json

from strategies import SAMPLE_TOKENS, build_sniper
from trading import SniperConfig, TradingContext
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message


def _ctx(mint: str, **cfg) -> TradingContext:
    return TradingContext(token=SAMPLE_TOKENS[mint], config=SniperConfig(**cfg))


# -- pure-rule fast path -----------------------------------------------------


async def test_rule_sniper_buys_good_token():
    g = build_sniper(llm_client=None)
    state = await g.run(State(context=_ctx("GOOD")))
    d = state.output
    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    assert [t.node for t in state.trace] == ["fast_safety", "fast_market", "rule_buy"]


async def test_rule_sniper_aborts_rug_instantly():
    g = build_sniper(llm_client=None)
    state = await g.run(State(context=_ctx("RUG")))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True
    # aborted at the very first node
    assert [t.node for t in state.trace] == ["fast_safety"]


async def test_rule_sniper_skips_thin_market():
    g = build_sniper(llm_client=None)
    state = await g.run(State(context=_ctx("LOWLIQ")))
    assert state.output.action == "skip"
    assert [t.node for t in state.trace] == ["fast_safety", "fast_market"]


async def test_size_respects_hard_cap():
    g = build_sniper(llm_client=None)
    state = await g.run(State(context=_ctx("GOOD", base_size=100.0, max_size=2.0)))
    assert state.output.size <= 2.0


# -- LLM-decide / hybrid -----------------------------------------------------


class _FakeLLM:
    def __init__(self, action="buy", size_pct=0.5, confidence=0.8):
        self._p = {
            "action": action,
            "size_pct": size_pct,
            "confidence": confidence,
            "reasoning": "go",
        }

    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


async def test_llm_decide_mode_produces_decision():
    g = build_sniper(_FakeLLM(action="buy", size_pct=0.5))
    ctx = _ctx("GOOD", use_llm=True, decision_mode="llm", max_size=4.0)
    state = await g.run(State(context=ctx))
    d = state.output
    assert d.action == "buy"
    assert d.size == 2.0  # 0.5 * max_size(4.0)
    assert "snipe_decide" in [t.node for t in state.trace]


async def test_hybrid_guardrail_caps_oversized_llm_request():
    # LLM asks for full size; guardrail caps at max_size
    g = build_sniper(_FakeLLM(action="buy", size_pct=1.0))
    ctx = _ctx("GOOD", use_llm=True, decision_mode="hybrid", max_size=3.0)
    state = await g.run(State(context=ctx))
    assert state.output.size <= 3.0


async def test_llm_path_still_aborts_rug_before_llm():
    # fast_safety must abort the rug before the LLM is ever called
    g = build_sniper(_FakeLLM(action="buy"))
    state = await g.run(State(context=_ctx("RUG", use_llm=True, decision_mode="hybrid")))
    assert state.output.action == "abort"
    assert "snipe_decide" not in [t.node for t in state.trace]


async def test_llm_failure_falls_back_to_skip_via_guardrail():
    class _Down:
        async def complete(self, *a, **k):
            from zetryn.llm import LLMError

            raise LLMError("down")

        async def aclose(self):
            pass

    g = build_sniper(_Down())
    state = await g.run(State(context=_ctx("GOOD", use_llm=True, decision_mode="hybrid")))
    assert state.output.action == "skip"
    assert state.output.flags["llm_failed"] is True


# -- hybrid_audit (M9) -------------------------------------------------------


class _AuditLLM:
    """Fake LLM that returns an AuditVerdict JSON."""

    def __init__(self, *, agrees: bool = True, concerns=None) -> None:
        self._p = {
            "agrees": agrees,
            "confidence": 0.85,
            "concerns": list(concerns or []),
            "reasoning": "audit ok" if agrees else "audit disagrees",
        }

    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="audit-fake", latency_ms=1.0)

    async def aclose(self):
        pass


async def test_hybrid_audit_returns_rule_decision_instantly_and_dispatches_task():
    """Sniper decides via rule, dispatches background LLM audit, returns immediately."""
    g = build_sniper(_AuditLLM(agrees=True))
    state = await g.run(State(context=_ctx("GOOD", decision_mode="hybrid_audit")))
    d = state.output

    # The decision came from the rule path (no snipe_decide in trace).
    assert d.action == "buy"
    assert d.size is not None and d.size > 0
    assert "snipe_decide" not in [t.node for t in state.trace]
    assert "audit_dispatch" in [t.node for t in state.trace]
    # Audit task was created but not awaited inside the graph.
    assert "audit_task" in state.scratch
    assert d.flags.get("audit_dispatched") is True


async def test_hybrid_audit_task_completes_with_verdict():
    """Awaiting the audit task yields a populated AuditVerdict."""
    from trading.schemas import AuditVerdict

    g = build_sniper(_AuditLLM(agrees=False, concerns=["holders too few"]))
    state = await g.run(State(context=_ctx("GOOD", decision_mode="hybrid_audit")))
    verdict: AuditVerdict = await state.scratch["audit_task"]

    assert isinstance(verdict, AuditVerdict)
    assert verdict.agrees is False
    assert verdict.concerns == ["holders too few"]


async def test_hybrid_audit_skips_dispatch_when_decision_is_not_buy():
    """No point auditing a skip/abort — only entries matter for learning loop."""
    g = build_sniper(_AuditLLM())
    state = await g.run(State(context=_ctx("RUG", decision_mode="hybrid_audit")))
    assert state.output.action == "abort"
    assert "audit_task" not in state.scratch
    assert "audit_dispatch" not in [t.node for t in state.trace]


async def test_hybrid_audit_swallows_llm_failure_into_verdict():
    """An LLM failure must NOT crash the background task — verdict carries the error."""
    from trading.schemas import AuditVerdict

    class _Down:
        async def complete(self, *a, **k):
            from zetryn.llm import LLMError

            raise LLMError("audit down")

        async def aclose(self):
            pass

    g = build_sniper(_Down())
    state = await g.run(State(context=_ctx("GOOD", decision_mode="hybrid_audit")))
    # Rule decision still returned instantly.
    assert state.output.action == "buy"
    # Audit task completes with a failure verdict (not raised).
    verdict: AuditVerdict = await state.scratch["audit_task"]
    assert verdict.agrees is False
    assert any("audit_failed" in c for c in verdict.concerns)
