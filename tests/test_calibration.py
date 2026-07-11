"""CalibrationMap + closed-trade replay bridge (confidence calibration layer)."""

import json

from strategies.backtest import (
    ClosedTrade,
    calibration_records,
    closed_trade_metrics,
    fit_calibration,
    replay_dataset,
)
from strategies.providers import SAMPLE_TOKENS
from zetryn.analytics import CalibrationMap, CalibrationRecord


def _records(n: int, score: float, win_rate: float, source: str | None = None):
    wins = round(n * win_rate)
    return [
        CalibrationRecord(score=score, won=i < wins, source=source)
        for i in range(n)
    ]


def test_empty_map_returns_raw_score():
    m = CalibrationMap.fit([])
    assert m.calibrate(0.65) == 0.65


def test_calibrate_converges_to_empirical_win_rate():
    # 200 trades at score ~0.65 that only win 30% of the time.
    m = CalibrationMap.fit(_records(200, 0.65, 0.30))
    assert abs(m.calibrate(0.65) - 0.30) < 0.02
    # A raw 0.65 is NOT taken at face value anymore.
    assert m.calibrate(0.65) < 0.4


def test_sparse_bin_shrinks_toward_global_rate():
    # Global book wins 50%; a single winning trade at 0.95 must not map to 1.0.
    records = _records(100, 0.55, 0.50) + [CalibrationRecord(score=0.95, won=True)]
    m = CalibrationMap.fit(records)
    v = m.calibrate(0.95)
    assert 0.5 < v < 0.7  # pulled well below the raw 1.0 empirical rate


def test_per_source_calibration_overrides_global_when_enough_data():
    records = _records(100, 0.65, 0.70, source="pumpfun") + _records(
        100, 0.65, 0.20, source="birdeye"
    )
    m = CalibrationMap.fit(records, min_source_samples=50)
    assert m.calibrate(0.65, source="pumpfun") > 0.6
    assert m.calibrate(0.65, source="birdeye") < 0.3
    # Unknown / sparse source falls back to the blended global bin (~0.45).
    blended = m.calibrate(0.65, source="brand-new-feed")
    assert 0.35 < blended < 0.55


def test_round_trip_serialization_preserves_lookup():
    m = CalibrationMap.fit(_records(80, 0.6, 0.4, source="pumpfun"))
    restored = CalibrationMap.from_dict(json.loads(json.dumps(m.to_dict())))
    assert restored.calibrate(0.6, source="pumpfun") == m.calibrate(
        0.6, source="pumpfun"
    )


def test_report_exposes_bin_stats():
    m = CalibrationMap.fit(_records(50, 0.65, 0.4))
    rep = m.report()
    assert rep["total"] == 50
    hot = [b for b in rep["bins"] if b["count"] > 0]
    assert hot and hot[0]["win_rate"] == 0.4


# -- closed-trade bridge ------------------------------------------------------


def _trade(i: int, *, conf, pnl, source="pumpfun", token=None) -> ClosedTrade:
    return ClosedTrade(
        trade_id=f"t{i}", source=source, confidence=conf, pnl_pct=pnl, token=token
    )


def test_calibration_records_skip_rows_without_confidence():
    trades = [_trade(1, conf=0.6, pnl=0.3), _trade(2, conf=None, pnl=-0.1)]
    recs = calibration_records(trades)
    assert len(recs) == 1 and recs[0].score == 0.6 and recs[0].won is True


def test_fit_calibration_from_trades():
    trades = [
        _trade(i, conf=0.65, pnl=0.5 if i < 30 else -0.15) for i in range(100)
    ]
    m = fit_calibration(trades)
    assert abs(m.calibrate(0.65, source="pumpfun") - 0.30) < 0.05


def test_replay_dataset_uses_only_rows_with_snapshots():
    snap = SAMPLE_TOKENS["GOOD"]
    trades = [
        _trade(1, conf=0.7, pnl=0.4, token=snap),
        _trade(2, conf=0.6, pnl=-0.2),  # no snapshot → not replayable
    ]
    items, outcomes = replay_dataset(trades)
    assert [i[0] for i in items] == ["t1"]
    assert outcomes["t1"].pnl_pct == 0.4


def test_closed_trade_metrics_breaks_down_by_source_and_confidence():
    trades = (
        [_trade(i, conf=0.65, pnl=0.5, source="pumpfun") for i in range(6)]
        + [_trade(10 + i, conf=0.65, pnl=-0.15, source="pumpfun") for i in range(4)]
        + [_trade(20 + i, conf=0.9, pnl=0.8, source="kol") for i in range(2)]
    )
    m = closed_trade_metrics(trades)
    assert m["overall"]["trades"] == 12
    assert m["by_source"]["pumpfun"]["win_rate"] == 0.6
    assert m["by_source"]["kol"]["win_rate"] == 1.0
    assert m["by_confidence"]["0.6-0.8"]["trades"] == 10
    assert m["by_confidence"]["0.8-1.0"]["trades"] == 2


async def test_scanner_confidence_is_calibrated_when_map_provided():
    """End-to-end: raw 0.85 final_score remaps to its empirical win rate."""
    from tests.test_scanner import _FakeLLM, _ctx
    from strategies import build_scanner
    from zetryn.core import State

    records = _records(200, 0.85, 0.40, source="pumpfun")
    m = CalibrationMap.fit(records, min_source_samples=50)

    g = build_scanner(_FakeLLM(final=0.85, rec="alert"), calibration=m)
    state = await g.run(State(context=_ctx("GOOD")))
    d = state.output
    assert d.flags["calibrated"] is True
    assert d.scores["final"] == 0.85  # raw score preserved
    src = state.context.token.source
    assert d.confidence == round(m.calibrate(0.85, source=src), 4)
    assert d.confidence < 0.5  # 0.85 raw ≠ 85% win rate


async def test_scanner_without_map_keeps_raw_confidence():
    from tests.test_scanner import _FakeLLM, _ctx
    from strategies import build_scanner
    from zetryn.core import State

    g = build_scanner(_FakeLLM(final=0.85, rec="alert"))
    state = await g.run(State(context=_ctx("GOOD")))
    assert state.output.confidence == 0.85
    assert state.output.flags["calibrated"] is False
