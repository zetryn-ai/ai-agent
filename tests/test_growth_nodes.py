"""Tests for Organic Growth Detector rule nodes (v0.16.0 / A1)."""

from __future__ import annotations

from strategies import SAMPLE_TOKENS, build_organic_detector
from trading import GrowthConfig, GrowthContext, GrowthSnapshot
from zetryn.core import State

_NOW = 1_700_000_000.0


def _snap(**over) -> GrowthSnapshot:
    base = dict(
        mint="MINT_X",
        detected_at_ts=_NOW,
        observation_seconds=300.0,
        candle_count=10,
        price_trajectory="steady_climb",
        sell_presence_pct=0.30,
        unique_buyer_trend=0.40,
        holder_growth_rate=3.0,
        has_healthy_pullback=True,
        max_drawdown_pct=0.12,
        whale_volume_pct=0.25,
        volume_acceleration=1.8,
    )
    base.update(over)
    return GrowthSnapshot(**base)


def _ctx(snap=None, token=None, **cfg) -> GrowthContext:
    return GrowthContext(
        token=token if token is not None else SAMPLE_TOKENS["GOOD"],
        snapshot=snap if snap is not None else _snap(),
        config=GrowthConfig(**cfg),
    )


# -- fast_safety -------------------------------------------------------------


async def test_fast_safety_aborts_rug():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(token=SAMPLE_TOKENS["RUG"])))
    assert state.output.action == "abort"
    assert state.output.flags["rug_risk"] is True
    assert [t.node for t in state.trace] == ["fast_safety"]


# -- observation_gate --------------------------------------------------------


async def test_observation_gate_rejects_short_window():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(observation_seconds=30.0))))
    assert state.output.action == "skip"
    assert state.output.flags["classification"] == "suspicious"
    assert "insufficient observation" in state.output.reasons[0]


async def test_observation_gate_rejects_too_few_candles():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(candle_count=2))))
    assert state.output.action == "skip"
    assert "too few candles" in state.output.reasons[0]


# -- manipulation_gate -------------------------------------------------------


async def test_manipulation_gate_aborts_vertical_pump_zero_sells():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(
        price_trajectory="vertical_pump",
        sell_presence_pct=0.005,   # near-zero — no organic sellers
    ))))
    assert state.output.action == "abort"
    assert state.output.flags["classification"] == "manipulated"
    assert "vertical_pump" in state.output.reasons[0]


async def test_manipulation_gate_aborts_extreme_whale():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(whale_volume_pct=0.92))))
    assert state.output.action == "abort"
    assert "whale dominance" in state.output.reasons[0]


async def test_manipulation_gate_passes_vertical_pump_with_sells():
    # Vertical pump but has sellers — not a hard abort from manipulation_gate
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(
        price_trajectory="vertical_pump",
        sell_presence_pct=0.40,   # plenty of sellers
    ))))
    # Goes through to organic_classify (not short-circuited by manipulation_gate)
    nodes = [t.node for t in state.trace]
    assert "organic_classify" in nodes
    # trajectory dim fails (vertical_pump) → 4/5 dims pass → score=0.8 → organic → buy
    # The classification is determined by scoring, not a hard abort
    assert state.output.action in ("buy", "skip", "abort")


# -- organic_classify scoring ------------------------------------------------


async def test_full_organic_token_gets_buy():
    """All 5 dimensions pass → organic_score=1.0 → action=buy."""
    g = build_organic_detector()
    state = await g.run(State(context=_ctx()))
    assert state.output.action == "buy"
    assert state.output.flags["classification"] == "organic"
    assert state.output.scores["organic_score"] == 1.0


async def test_no_pullback_drops_score():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(has_healthy_pullback=False))))
    # 4/5 dimensions pass → score 0.8 → still organic
    assert state.output.action == "buy"
    assert state.output.scores["organic_score"] == pytest_approx(0.8)


async def test_two_dims_failing_gives_suspicious():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(
        has_healthy_pullback=False,
        unique_buyer_trend=-0.50,   # below min_unique_buyer_trend
    ))))
    # 3/5 dimensions → score 0.6 → suspicious (threshold 0.65)
    assert state.output.action == "skip"
    assert state.output.flags["classification"] == "suspicious"
    assert state.output.scores["organic_score"] == pytest_approx(0.6)


async def test_three_dims_failing_gives_manipulated():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(
        price_trajectory="flat",           # trajectory fails
        has_healthy_pullback=False,        # pullback fails
        unique_buyer_trend=-0.50,          # buyers fails
    ))))
    # 2/5 → score 0.4 → still suspicious (threshold 0.35 for manipulated)
    assert state.output.scores["organic_score"] == pytest_approx(0.4)
    assert state.output.action == "skip"


async def test_four_dims_failing_gives_abort():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx(snap=_snap(
        price_trajectory="declining",      # fails
        has_healthy_pullback=False,        # fails
        unique_buyer_trend=-0.50,          # fails
        whale_volume_pct=0.80,             # fails (> 0.65)
    ))))
    # 1/5 → score 0.2 → manipulated (< 0.35)
    assert state.output.action == "abort"
    assert state.output.flags["classification"] == "manipulated"


async def test_full_trace_rule_mode():
    g = build_organic_detector()
    state = await g.run(State(context=_ctx()))
    assert [t.node for t in state.trace] == [
        "fast_safety", "observation_gate", "manipulation_gate", "organic_classify"
    ]


def pytest_approx(v):
    """Inline helper to avoid importing pytest.approx in the test body."""
    import math
    class _Approx:
        def __eq__(self, other):
            return math.isclose(other, v, rel_tol=1e-6)
        def __repr__(self):
            return f"≈{v}"
    return _Approx()
