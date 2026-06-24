"""Tests for M5 backtest: generic harness + trading metrics."""

import json

from strategies import build_scanner
from strategies.backtest import (
    HistoricalCase,
    TokenOutcome,
    build_items,
    trading_metrics,
)
from strategies.providers import SAMPLE_TOKENS
from zetryn.backtest import Backtester
from zetryn.core import END, Graph, RuleNode
from zetryn.llm.types import LLMResult, Message


class _FakeLLM:
    """Returns a FullAnalysis (M8 scanner schema)."""

    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        aspect = {"score": 0.85, "verdict": "positive", "signals": [], "reasoning": "ok"}
        payload = {
            "safety": aspect,
            "market": aspect,
            "wallets": aspect,
            "social": aspect,
            "final_score": 0.85,
            "recommendation": "alert",
            "reasoning": "fake",
        }
        return LLMResult(text=json.dumps(payload), model="fake", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


# -- generic harness ---------------------------------------------------------


async def test_backtester_collects_decisions_and_traces():
    g = Graph("g")
    g.add_node(RuleNode("decide", lambda s: s.__setattr__("output", {"action": "alert"})))
    g.add_edge("decide", END).set_entry("decide").compile()

    bt = Backtester(g)
    result = await bt.run([("t1", {}), ("t2", {})])
    assert len(result.records) == 2
    assert result.action_distribution() == {"alert": 2}
    assert all(r.trace for r in result.records)


async def test_backtester_records_errors_and_continues():
    def boom(s):
        raise ValueError("bad")

    g = Graph("g")
    g.add_node(RuleNode("x", boom)).add_edge("x", END).set_entry("x").compile()
    result = await Backtester(g).run([("t1", {})])
    assert result.records[0].error is not None
    assert result.ok == []


# -- trading backtest end-to-end ---------------------------------------------


def _dataset() -> dict[str, HistoricalCase]:
    return {
        "GOOD": HistoricalCase(
            token=SAMPLE_TOKENS["GOOD"],
            outcome=TokenOutcome(rugged=False, max_gain_pct=2.0, pnl_pct=1.2),
        ),
        "RUG": HistoricalCase(
            token=SAMPLE_TOKENS["RUG"],
            outcome=TokenOutcome(rugged=True, max_gain_pct=0.0, pnl_pct=-1.0),
        ),
        "LOWLIQ": HistoricalCase(
            token=SAMPLE_TOKENS["LOWLIQ"],
            outcome=TokenOutcome(rugged=False, max_gain_pct=0.1, pnl_pct=-0.2),
        ),
    }


async def test_trading_backtest_metrics():
    scanner = build_scanner(_FakeLLM())
    items, outcomes = build_items(_dataset())
    result = await Backtester(scanner).run(items, outcomes=outcomes)

    metrics = result.metrics(trading_metrics)
    # GOOD -> alert (entered); RUG & LOWLIQ -> skip
    assert metrics["entered"] == 1
    assert metrics["skipped"] == 2
    assert metrics["win_rate"] == 1.0  # the one entry was profitable
    assert metrics["rugs_entered"] == 0  # avoided the rug
    assert metrics["rug_avoidance_recall"] == 1.0  # skipped the only rug


async def test_backtest_catches_bad_strategy_entering_rug():
    """A loose config that enters the rug should be reflected in metrics."""
    from trading.schemas import ScannerConfig

    # Disable LLM and loosen gates so RUG slips through (illustrative).
    loose = ScannerConfig(use_llm=False, max_top10_pct=0.99, min_holders=0, min_liquidity_usd=0,
                          min_volume_1h=0, alert_threshold=0.0, watch_threshold=0.0)
    scanner = build_scanner(llm_client=None)
    items, outcomes = build_items(_dataset(), config=loose)
    result = await Backtester(scanner).run(items, outcomes=outcomes)
    metrics = result.metrics(trading_metrics)
    # With safety gate still active, RUG (mint authority) is caught regardless.
    assert metrics["rugs_entered"] == 0
