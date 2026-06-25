"""Integration tests: ReflectiveNode wired into the scanner closes the
learning loop — past losers are summarised and injected into the analyst
system prompt of the next run.
"""

from __future__ import annotations

import json

import pytest

from strategies import SAMPLE_TOKENS, build_scanner
from trading import ScannerConfig, TradingContext
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message
from zetryn.memory import DecisionLog, InMemoryStore


class _RecordingLLM:
    """Captures the messages the analyst sees so we can assert injection."""

    def __init__(self) -> None:
        self.received: list[list[Message]] = []
        self._payload = {
            "safety":  {"score": 0.8, "verdict": "positive", "signals": [], "reasoning": "fake"},
            "market":  {"score": 0.7, "verdict": "positive", "signals": [], "reasoning": "fake"},
            "wallets": {"score": 0.7, "verdict": "positive", "signals": [], "reasoning": "fake"},
            "social":  {"score": 0.7, "verdict": "positive", "signals": [], "reasoning": "fake"},
            "final_score": 0.75,
            "recommendation": "watch",
            "reasoning": "fake",
        }

    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        self.received.append(messages)
        return LLMResult(text=json.dumps(self._payload), model="fake", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


def _system_text(call: list[Message]) -> str:
    return "\n".join(m["content"] for m in call if m["role"] == "system")


@pytest.mark.asyncio
async def test_scanner_without_decision_log_skips_reflect_node():
    """Backwards-compat: an LLM-only build does not run the reflect node."""
    llm = _RecordingLLM()
    g = build_scanner(llm)  # no decision_log
    state = await g.run(State(context=TradingContext(token=SAMPLE_TOKENS["GOOD"])))

    assert state.output.action == "watch"
    nodes_run = [t.node for t in state.trace]
    assert "reflect" not in nodes_run
    # lessons_text must not be present
    assert "lessons_text" not in state.scratch


@pytest.mark.asyncio
async def test_scanner_with_empty_decision_log_runs_reflect_with_no_lessons():
    """With an empty log, reflect runs but lessons_text says 'no prior'."""
    log = DecisionLog(InMemoryStore())
    llm = _RecordingLLM()
    g = build_scanner(llm, decision_log=log)

    state = await g.run(State(context=TradingContext(token=SAMPLE_TOKENS["GOOD"])))

    nodes_run = [t.node for t in state.trace]
    assert "reflect" in nodes_run
    assert "lessons_text" in state.scratch
    assert "No prior decisions" in state.scratch["lessons_text"]
    # Even with empty log we still inject the lessons block — it's harmless
    sys_text = _system_text(llm.received[0])
    assert "No prior decisions" in sys_text


@pytest.mark.asyncio
async def test_scanner_with_losing_history_injects_lessons():
    """Real test: past losing decisions become a lessons block in the prompt."""
    log = DecisionLog(InMemoryStore())
    # Seed two losers with a common feature pattern: source=pumpfun + high top10
    await log.log("PF26", {"top10_pct": 0.38, "source": "pumpfun"})
    await log.record_outcome("PF26", {"pnl": -0.26})
    await log.log("ILY", {"top10_pct": 0.40, "source": "pumpfun"})
    await log.record_outcome("ILY", {"pnl": -0.21})

    llm = _RecordingLLM()
    g = build_scanner(
        llm, decision_log=log, reflect_feature_keys=["source", "top10_pct"]
    )
    await g.run(State(context=TradingContext(token=SAMPLE_TOKENS["GOOD"])))

    sys_text = _system_text(llm.received[0])
    assert "Lessons from recent decisions" in sys_text
    # Loser ids surfaced
    assert "PF26" in sys_text
    assert "ILY" in sys_text
    # At least one of the loss patterns named
    assert "pumpfun" in sys_text or "top10_pct" in sys_text


@pytest.mark.asyncio
async def test_reflect_does_not_run_on_hard_gate_failure():
    """Reflect must not waste a memory read on tokens rejected by hard gates."""
    log = DecisionLog(InMemoryStore())
    await log.log("L", {"source": "x"})
    await log.record_outcome("L", {"pnl": -0.1})

    llm = _RecordingLLM()
    g = build_scanner(llm, decision_log=log)

    # RUG is a known hard-gate reject in the sample fixtures.
    state = await g.run(State(context=TradingContext(token=SAMPLE_TOKENS["RUG"])))

    nodes_run = [t.node for t in state.trace]
    assert "reject" in nodes_run
    assert "reflect" not in nodes_run
    assert llm.received == []  # analyst never called either


@pytest.mark.asyncio
async def test_lessons_layered_after_knowledge_pack(tmp_path):
    """Layering order: pack blocks first, then lessons, then analyst persona."""
    from zetryn.knowledge import KnowledgePack

    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "01-rules.md").write_text("House rule: skip ATH.")
    pack = KnowledgePack.from_dir(tmp_path)

    log = DecisionLog(InMemoryStore())
    await log.log("L1", {"source": "pumpfun"})
    await log.record_outcome("L1", {"pnl": -0.2})

    llm = _RecordingLLM()
    g = build_scanner(
        llm, knowledge_pack=pack, decision_log=log, reflect_feature_keys=["source"]
    )
    await g.run(State(context=TradingContext(token=SAMPLE_TOKENS["GOOD"])))

    msgs = llm.received[0]
    system_msgs = [m["content"] for m in msgs if m["role"] == "system"]
    pack_idx = next(i for i, c in enumerate(system_msgs) if "House rule: skip ATH." in c)
    lessons_idx = next(i for i, c in enumerate(system_msgs) if "Lessons from recent" in c)
    persona_idx = next(i for i, c in enumerate(system_msgs) if "memecoin analyst" in c.lower())
    # Layering: pack block → lessons block → analyst persona.
    assert pack_idx < lessons_idx < persona_idx


@pytest.mark.asyncio
async def test_reflect_window_parameter_limits_lookback():
    """reflect_window caps how many past records are summarised."""
    log = DecisionLog(InMemoryStore())
    for i in range(10):
        await log.log(f"r{i}", {"source": "X"})
        await log.record_outcome(f"r{i}", {"pnl": -0.1})

    llm = _RecordingLLM()
    g = build_scanner(
        llm, decision_log=log, reflect_window=3, reflect_feature_keys=["source"]
    )
    state = await g.run(State(context=TradingContext(token=SAMPLE_TOKENS["GOOD"])))

    result = state.scratch["lessons"]
    assert result.total_decisions == 3  # only last 3 considered


@pytest.mark.asyncio
async def test_reflect_skipped_when_no_llm():
    """Without an LLM, the reflect node makes no sense — it must not be added."""
    log = DecisionLog(InMemoryStore())
    g = build_scanner(llm_client=None, decision_log=log)
    ctx = TradingContext(token=SAMPLE_TOKENS["GOOD"], config=ScannerConfig())
    state = await g.run(State(context=ctx))
    nodes_run = [t.node for t in state.trace]
    assert "reflect" not in nodes_run
    assert "analyst" not in nodes_run
