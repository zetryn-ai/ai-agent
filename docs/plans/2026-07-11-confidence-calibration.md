# Confidence Calibration + Production Replay Bridge

**Date:** 2026-07-11
**Status:** Shipped (v1.2.0)

## Problem

`Decision.confidence` is the analyst LLM's raw `final_score`. LLM scores
cluster around 0.5/0.6/0.65 and carry no probabilistic meaning — a 0.65 does
not win 65% of the time — yet the bot sizes positions as
`base_size × confidence`. Separately, the backtest harness had no bridge to
production outcomes: with paper trades accumulating in the VPS Postgres there
was no systematic way to ask "which prompt/gate/source is working".

## Decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Where the primitive lives | New `zetryn/analytics/` package — domain-agnostic (`(score, won, source)` tuples), no imports from `trading/`, no I/O. The bot exports rows; the framework computes. |
| 2 | Calibration method | Histogram binning over [0,1] (default 10 bins) with shrinkage: each bin's win rate is shrunk toward the global rate by `prior_strength` pseudo-counts; per-source bins shrink toward the global bin and only activate at `min_source_samples`. Sparse data degrades toward the aggregate instead of overfitting. |
| 3 | Fallback chain | source bin → global bin → global rate → raw score (empty map). `calibrate()` never fails. |
| 4 | Integration point | `build_scanner(..., calibration=)` → `decide.make_finalize(calibration)`. Calibrated value becomes `Decision.confidence` (what the bot sizes on); raw score stays in `scores["final"]`, calibrated copy in `scores["calibrated"]`, `flags["calibrated"]=True`. |
| 5 | Serialization | `to_dict()`/`from_dict()` — plain JSON-safe data, so the bot can fit offline (cron) and ship the map like a knowledge asset. |
| 6 | Replay bridge | `strategies/backtest.py` gains `ClosedTrade` (the export shape), `fit_calibration(trades)`, `replay_dataset(trades)` (re-run the current graph over entry-time snapshots vs realized outcomes), and `closed_trade_metrics(trades)` (win-rate/PnL per source + per confidence band). |

## Shape

```python
from strategies.backtest import ClosedTrade, fit_calibration, closed_trade_metrics
from strategies import build_scanner

trades = [ClosedTrade(**row) for row in exported_rows]   # bot does the SQL
cal = fit_calibration(trades)                            # score → win rate
agent = build_scanner(llm, calibration=cal)              # confidence is now empirical
report = closed_trade_metrics(trades)                    # by_source / by_confidence
```

## Out of scope (follow-ups)

- Isotonic/Platt calibration — binning + shrinkage is enough until the sample
  size grows past a few thousand trades.
- Bot-side wiring (export query, fit cadence, persistence of the fitted map) —
  bot repo work, tracked there.
- Auto re-fit inside the framework — would require I/O; boundary says no.
