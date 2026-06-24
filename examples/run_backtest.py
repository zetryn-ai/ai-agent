"""Example: backtest the scanner over a small historical dataset.

Runs offline (stub LLM). Shows how you'd compare a strategy against known outcomes
before risking real money: win-rate, simulated PnL, and rug-avoidance.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import build_scanner
from strategies.backtest import HistoricalCase, TokenOutcome, build_items, trading_metrics
from strategies.providers import SAMPLE_TOKENS
from zetryn.backtest import Backtester
from zetryn.llm.types import LLMResult, Message


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {"score": 0.8, "sentiment": "bullish", "rug_signals": [], "reasoning": "ok"}
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


# Historical token snapshots paired with what actually happened.
DATASET = {
    "GOOD": HistoricalCase(
        SAMPLE_TOKENS["GOOD"], TokenOutcome(rugged=False, max_gain_pct=2.0, pnl_pct=1.2)
    ),
    "RUG": HistoricalCase(
        SAMPLE_TOKENS["RUG"], TokenOutcome(rugged=True, max_gain_pct=0.0, pnl_pct=-1.0)
    ),
    "LOWLIQ": HistoricalCase(
        SAMPLE_TOKENS["LOWLIQ"], TokenOutcome(rugged=False, max_gain_pct=0.1, pnl_pct=-0.2)
    ),
}


async def main() -> None:
    scanner = build_scanner(_StubLLM())
    items, outcomes = build_items(DATASET)
    result = await Backtester(scanner).run(items, outcomes=outcomes)

    print("Per-token decisions:")
    for r in result.records:
        action = getattr(r.decision, "action", "?")
        o = r.outcome
        print(f"  {r.item_id:8} -> {action:6} | rugged={o.rugged} pnl={o.pnl_pct}")

    print("\nAction distribution:", result.action_distribution())
    print("\nTrading metrics:")
    print(json.dumps(result.metrics(trading_metrics), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
