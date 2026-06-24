"""Trading-specific backtest: historical dataset, outcomes, and metrics.

Pairs each historical ``TokenInput`` with what actually happened (``TokenOutcome``),
runs the scanner over them via the generic :class:`zetryn.backtest.Backtester`, and
scores the decisions: simulated PnL, hit rate, and rug-avoidance precision/recall.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from trading.schemas import ScannerConfig, TokenInput, TradingContext
from zetryn.backtest import RunRecord


class TokenOutcome(BaseModel):
    """What actually happened to a token after the decision point."""

    rugged: bool = False
    max_gain_pct: float = 0.0  # peak gain after decision, e.g. 1.5 = +150%
    pnl_pct: float = 0.0  # realized PnL of a simple buy-and-exit rule (fraction)


@dataclass
class HistoricalCase:
    token: TokenInput
    outcome: TokenOutcome


def build_items(
    dataset: dict[str, HistoricalCase], config: ScannerConfig | None = None
) -> tuple[list[tuple[str, TradingContext]], dict[str, Any]]:
    """Turn a dataset into (items, outcomes) for the Backtester."""
    cfg = config or ScannerConfig()
    items = [
        (cid, TradingContext(token=case.token, config=cfg)) for cid, case in dataset.items()
    ]
    outcomes = {cid: case.outcome for cid, case in dataset.items()}
    return items, outcomes


# Actions that mean "we would have entered a position".
ENTRY_ACTIONS = {"alert", "buy"}


def trading_metrics(records: list[RunRecord]) -> dict[str, Any]:
    """Score backtest records with trading-relevant metrics."""
    entered = [r for r in records if _action(r) in ENTRY_ACTIONS and r.outcome is not None]
    skipped = [r for r in records if _action(r) not in ENTRY_ACTIONS and r.outcome is not None]

    # PnL & hit rate over entered positions.
    pnls = [r.outcome.pnl_pct for r in entered]
    wins = sum(1 for p in pnls if p > 0)
    total_pnl = sum(pnls)

    # Rug avoidance. Positive = a token that actually rugged.
    all_with_outcome = entered + skipped
    rugs = [r for r in all_with_outcome if r.outcome.rugged]
    rugs_entered = [r for r in entered if r.outcome.rugged]
    rugs_skipped = [r for r in skipped if r.outcome.rugged]

    # recall = rugs we avoided / all rugs; precision = clean entries / all entries
    rug_recall = len(rugs_skipped) / len(rugs) if rugs else None
    clean_entries = len(entered) - len(rugs_entered)
    entry_precision = clean_entries / len(entered) if entered else None

    return {
        "total": len(records),
        "entered": len(entered),
        "skipped": len(skipped),
        "win_rate": round(wins / len(entered), 4) if entered else None,
        "avg_pnl_pct": round(total_pnl / len(entered), 4) if entered else None,
        "total_pnl_pct": round(total_pnl, 4),
        "rugs_total": len(rugs),
        "rugs_entered": len(rugs_entered),  # the costly mistakes
        "rug_avoidance_recall": round(rug_recall, 4) if rug_recall is not None else None,
        "entry_precision": round(entry_precision, 4) if entry_precision is not None else None,
    }


def _action(record: RunRecord) -> str:
    d = record.decision
    if d is None:
        return "error"
    return getattr(d, "action", "unknown")
