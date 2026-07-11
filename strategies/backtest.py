"""Trading-specific backtest: historical dataset, outcomes, and metrics.

Pairs each historical ``TokenInput`` with what actually happened (``TokenOutcome``),
runs the scanner over them via the generic :class:`zetryn.backtest.Backtester`, and
scores the decisions: simulated PnL, hit rate, and rug-avoidance precision/recall.

Also the production replay bridge: the bot exports its realized trades as
:class:`ClosedTrade` rows (plain data, framework does no I/O) and this module
turns them into (a) a fitted :class:`~zetryn.analytics.CalibrationMap` via
:func:`fit_calibration` and (b) a replayable dataset + per-source /
per-confidence breakdowns via :func:`replay_dataset` / :func:`closed_trade_metrics`
— the systematic answer to "which prompt/gate/source is actually working".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from trading.schemas import ScannerConfig, TokenInput, TradingContext
from zetryn.analytics import CalibrationMap, CalibrationRecord
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


# -- production replay bridge (closed trades → calibration / metrics) ---------


class ClosedTrade(BaseModel):
    """One realized trade exported from the bot's outcome store.

    The bot owns the database; it maps its ``closed_trades`` rows into this
    shape (one dict per row is enough — ``ClosedTrade(**row)``). ``token`` is
    the entry-time ``TokenInput`` snapshot when the bot stored one; only rows
    that carry it can be *re-run* through a graph, but every row contributes
    to calibration and metrics.
    """

    trade_id: str
    source: str | None = None
    action: str = "alert"
    confidence: float | None = None  # Decision.confidence at entry
    pnl_pct: float  # realized, signed fraction (+0.3 = +30%)
    rugged: bool = False
    max_gain_pct: float = 0.0
    token: TokenInput | None = None

    @property
    def won(self) -> bool:
        return self.pnl_pct > 0


def calibration_records(trades: list[ClosedTrade]) -> list[CalibrationRecord]:
    """Rows usable for calibration: those that recorded an entry confidence."""
    return [
        CalibrationRecord(score=t.confidence, won=t.won, source=t.source)
        for t in trades
        if t.confidence is not None
    ]


def fit_calibration(trades: list[ClosedTrade], **fit_kwargs: Any) -> CalibrationMap:
    """Fit a :class:`CalibrationMap` straight from exported closed trades."""
    return CalibrationMap.fit(calibration_records(trades), **fit_kwargs)


def replay_dataset(
    trades: list[ClosedTrade], config: ScannerConfig | None = None
) -> tuple[list[tuple[str, TradingContext]], dict[str, Any]]:
    """(items, outcomes) for ``Backtester.run`` from trades with token snapshots.

    Re-running the current graph over entry-time snapshots and comparing the
    fresh decisions against realized outcomes shows what a prompt/gate change
    would have done to the live book.
    """
    with_snapshot = [t for t in trades if t.token is not None]
    dataset = {
        t.trade_id: HistoricalCase(
            token=t.token,
            outcome=TokenOutcome(
                rugged=t.rugged, max_gain_pct=t.max_gain_pct, pnl_pct=t.pnl_pct
            ),
        )
        for t in with_snapshot
    }
    return build_items(dataset, config)


class _Bucket(BaseModel):
    trades: int = 0
    wins: int = 0
    total_pnl_pct: float = 0.0
    pnls: list[float] = Field(default_factory=list, exclude=True)

    def add(self, t: ClosedTrade) -> None:
        self.trades += 1
        if t.won:
            self.wins += 1
        self.total_pnl_pct += t.pnl_pct
        self.pnls.append(t.pnl_pct)

    def summary(self) -> dict[str, Any]:
        return {
            "trades": self.trades,
            "win_rate": round(self.wins / self.trades, 4) if self.trades else None,
            "avg_pnl_pct": round(self.total_pnl_pct / self.trades, 4)
            if self.trades
            else None,
            "total_pnl_pct": round(self.total_pnl_pct, 4),
        }


def closed_trade_metrics(
    trades: list[ClosedTrade], *, confidence_bins: int = 5
) -> dict[str, Any]:
    """Aggregate realized performance by source and by confidence band.

    This is the evidence layer for tuning: if the 0.6–0.8 band wins at 30%
    while 0.8–1.0 wins at 70%, the alert threshold (and sizing) should say so.
    """
    overall = _Bucket()
    by_source: dict[str, _Bucket] = {}
    by_conf: dict[str, _Bucket] = {}

    width = 1.0 / confidence_bins
    for t in trades:
        overall.add(t)
        by_source.setdefault(t.source or "unknown", _Bucket()).add(t)
        if t.confidence is not None:
            idx = min(int(max(0.0, min(1.0, t.confidence)) * confidence_bins),
                      confidence_bins - 1)
            label = f"{idx * width:.1f}-{(idx + 1) * width:.1f}"
            by_conf.setdefault(label, _Bucket()).add(t)

    return {
        "overall": overall.summary(),
        "by_source": {k: b.summary() for k, b in sorted(by_source.items())},
        "by_confidence": {k: b.summary() for k, b in sorted(by_conf.items())},
    }
