"""Tests for Smart Money Confluence mode wiring (v0.14.0 / S5)."""

from __future__ import annotations

import json


from strategies import SAMPLE_TOKENS, SmartWalletRegistry, build_confluence
from trading import (
    ConfluenceConfig,
    ConfluenceContext,
    ConfluenceEvent,
    SmartWalletAccumulation,
    SmartWalletProfile,
)
from zetryn.core import State
from zetryn.llm.types import LLMResult
from zetryn.memory import DecisionLog, InMemoryStore

_NOW = 1_700_000_000.0
_WALLETS = {
    "wallet_A": SmartWalletProfile(hit_rate=0.6, tier="A"),
    "wallet_B": SmartWalletProfile(hit_rate=0.55, tier="A"),
    "wallet_C": SmartWalletProfile(hit_rate=0.5, tier="B"),
    "wallet_D": SmartWalletProfile(hit_rate=0.45, tier="B"),
    "wallet_E": SmartWalletProfile(hit_rate=0.4, tier="B"),
}
_REGISTRY = SmartWalletRegistry(_WALLETS, min_tier="B", min_hit_rate=0.35)


def _event() -> ConfluenceEvent:
    return ConfluenceEvent(
        mint="MINT_X",
        detected_at_ts=_NOW,
        window_seconds=7 * 24 * 3600,
        accumulations=[
            SmartWalletAccumulation(
                wallet=w, mint="MINT_X", sol_amount=1.5,
                detected_at_ts=_NOW, block_age_seconds=3.0,
            )
            for w in _WALLETS
        ],
    )


def _ctx(**cfg) -> ConfluenceContext:
    return ConfluenceContext(
        token=SAMPLE_TOKENS["GOOD"],
        event=_event(),
        config=ConfluenceConfig(**cfg),
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
    def __init__(self, *, agrees=True, concerns=None):
        self._p = {
            "agrees": agrees,
            "confidence": 0.85,
            "concerns": list(concerns or []),
            "reasoning": "audit ok",
        }

    async def complete(self, messages, **kw) -> LLMResult:
        return LLMResult(text=json.dumps(self._p), model="fake", latency_ms=1.0)

    async def aclose(self):
        pass


# -- rule mode ---------------------------------------------------------------


async def test_rule_mode_no_llm():
    g = build_confluence(llm_client=None, registry=_REGISTRY)
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "confluence_decide" not in nodes
    assert "audit_dispatch" not in nodes


# -- llm mode ----------------------------------------------------------------


async def test_llm_mode_routes_to_decide():
    g = build_confluence(llm_client=_FakeLLM(), registry=_REGISTRY)
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "buy"
    nodes = [t.node for t in state.trace]
    assert "confluence_decide" in nodes
    assert "rule_buy" not in nodes


async def test_llm_mode_skip_propagates():
    g = build_confluence(llm_client=_FakeLLM(action="skip"), registry=_REGISTRY)
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    assert state.output.action == "skip"


# -- hybrid mode -------------------------------------------------------------


async def test_hybrid_mode_guardrail_caps_size():
    llm = _FakeLLM(action="buy", size_pct=1.0)  # LLM wants max size
    g = build_confluence(llm_client=llm, registry=_REGISTRY)
    state = await g.run(State(context=_ctx(decision_mode="hybrid", max_size=2.0)))
    assert state.output.action == "buy"
    assert state.output.size is not None and state.output.size <= 2.0


async def test_hybrid_mode_guardrail_aborts_rug():
    llm = _FakeLLM(action="buy", size_pct=0.5)
    g = build_confluence(llm_client=llm, registry=_REGISTRY)
    state = await g.run(State(context=ConfluenceContext(
        token=SAMPLE_TOKENS["RUG"],
        event=_event(),
        config=ConfluenceConfig(decision_mode="hybrid"),
    )))
    # fast_safety catches rug before guardrail even runs
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True


# -- hybrid_audit mode -------------------------------------------------------


async def test_hybrid_audit_dispatches_for_buy():
    g = build_confluence(llm_client=_AuditLLM(), registry=_REGISTRY)
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    nodes = [t.node for t in state.trace]
    assert "rule_buy" in nodes
    assert "audit_dispatch" in nodes
    assert "confluence_decide" not in nodes
    assert state.output.flags.get("audit_dispatched") is True
    assert "audit_task" in state.scratch


async def test_hybrid_audit_no_audit_task_on_gate_reject():
    g = build_confluence(llm_client=_AuditLLM(), registry=_REGISTRY)
    # Make confluence_gate fail so graph short-circuits before audit_dispatch
    empty_ev = ConfluenceEvent(mint="X", detected_at_ts=_NOW, window_seconds=3600, accumulations=[])
    state = await g.run(State(context=ConfluenceContext(
        token=SAMPLE_TOKENS["GOOD"],
        event=empty_ev,
        config=ConfluenceConfig(decision_mode="hybrid_audit"),
    )))
    assert state.output.action == "skip"
    # audit_dispatch never ran — no audit_task in scratch
    assert "audit_task" not in state.scratch


# -- reflective loop (llm mode with decision_log) ----------------------------


async def test_reflect_node_inserted_with_decision_log():
    log = DecisionLog(InMemoryStore())
    g = build_confluence(
        llm_client=_FakeLLM(),
        registry=_REGISTRY,
        decision_log=log,
    )
    state = await g.run(State(context=_ctx(decision_mode="llm")))
    nodes = [t.node for t in state.trace]
    assert "reflect" in nodes
    idx_reflect = nodes.index("reflect")
    idx_decide = nodes.index("confluence_decide")
    assert idx_reflect < idx_decide


async def test_reflect_not_inserted_in_hybrid_audit():
    log = DecisionLog(InMemoryStore())
    g = build_confluence(
        llm_client=_FakeLLM(),
        registry=_REGISTRY,
        decision_log=log,
    )
    state = await g.run(State(context=_ctx(decision_mode="hybrid_audit")))
    nodes = [t.node for t in state.trace]
    assert "reflect" not in nodes


# -- SmartWalletRegistry -----------------------------------------------------


def test_registry_from_pack():
    from zetryn.knowledge import KnowledgePack
    import json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "data").mkdir()
        payload = {
            "wallets": {
                "addr1": {"hit_rate": 0.6, "avg_pnl_pct": 1.5, "trades_30d": 30, "tier": "A", "min_sol_to_copy": 0.5},
            },
            "min_tier_to_use": "A",
            "min_hit_rate": 0.4,
        }
        (p / "data" / "smart_wallet_whitelist.json").write_text(json.dumps(payload))
        pack = KnowledgePack.from_dir(p)

    from strategies import SmartWalletRegistry
    reg = SmartWalletRegistry.from_pack(pack)
    assert "addr1" in reg
    assert reg.min_tier == "A"
    assert reg.min_hit_rate == 0.4
    profile = reg.get("addr1")
    assert profile is not None
    assert profile.hit_rate == 0.6
    assert profile.tier == "A"


def test_registry_empty_when_no_pack_data():
    from zetryn.knowledge import KnowledgePack
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        pack = KnowledgePack.from_dir(p)

    from strategies import SmartWalletRegistry
    reg = SmartWalletRegistry.from_pack(pack)
    assert len(reg) == 0


def test_registry_passes_global_floor():
    reg = SmartWalletRegistry(
        {"w1": SmartWalletProfile(hit_rate=0.6, tier="A")},
        min_tier="B",
        min_hit_rate=0.4,
    )
    p_good = SmartWalletProfile(hit_rate=0.6, tier="A")
    p_low_hr = SmartWalletProfile(hit_rate=0.3, tier="A")
    p_low_tier = SmartWalletProfile(hit_rate=0.6, tier="C")
    assert reg.passes_global_floor(p_good) is True
    assert reg.passes_global_floor(p_low_hr) is False
    assert reg.passes_global_floor(p_low_tier) is False
