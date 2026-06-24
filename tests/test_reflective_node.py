"""Tests for the ReflectiveNode and underlying `reflect()` extractor."""

from __future__ import annotations

import pytest

from zetryn.core.state import State
from zetryn.memory import (
    DecisionLog,
    InMemoryStore,
    Pattern,
    ReflectionResult,
    ReflectiveNode,
    reflect,
)


def _record(run_id: str, *, pnl: float | None = None, **features) -> dict:
    rec = {"run_id": run_id, "action": "buy", **features}
    if pnl is not None:
        rec["outcome"] = {"pnl": pnl}
    return rec


# -- reflect() pure function ------------------------------------------------


def test_reflect_empty_records():
    r = reflect([])
    assert r.total_decisions == 0
    assert r.total_losses == 0
    assert r.patterns == []
    assert "No prior decisions" in r.to_text()


def test_reflect_ignores_records_without_outcome():
    records = [
        _record("a", top10_pct=0.3),  # no outcome
        _record("b", top10_pct=0.2, pnl=0.1),
    ]
    r = reflect(records)
    assert r.total_decisions == 1
    assert r.total_losses == 0


def test_reflect_counts_losers():
    records = [
        _record("win-1", pnl=0.20, top10_pct=0.20),
        _record("loss-1", pnl=-0.26, top10_pct=0.38),
        _record("loss-2", pnl=-0.21, top10_pct=0.40),
        _record("win-2", pnl=0.15, top10_pct=0.18),
    ]
    r = reflect(records, feature_keys=["top10_pct"])
    assert r.total_decisions == 4
    assert r.total_losses == 2
    assert r.avg_loss_pnl is not None
    assert r.avg_loss_pnl == pytest.approx(-0.235, abs=1e-3)
    assert "loss-1" in r.losing_ids and "loss-2" in r.losing_ids


def test_reflect_buckets_numeric_feature_by_quartile():
    # Build a population where high top10_pct -> losses, low -> wins.
    records = []
    for i in range(8):
        is_loss = i >= 4
        records.append(
            _record(
                f"r{i}",
                pnl=-0.20 if is_loss else 0.10,
                top10_pct=0.10 + 0.05 * i,  # 0.10, 0.15, ..., 0.45
            )
        )
    r = reflect(records, feature_keys=["top10_pct"], top_k=10)
    assert r.total_losses == 4
    # Pattern with most losses should be the highest bucket.
    top = r.patterns[0]
    assert top.feature == "top10_pct"
    assert top.loss_count >= 1
    assert top.loss_rate > 0


def test_reflect_buckets_categorical_feature():
    records = [
        _record("a", pnl=-0.10, source="pumpfun"),
        _record("b", pnl=-0.20, source="pumpfun"),
        _record("c", pnl=0.30, source="raydium"),
        _record("d", pnl=0.15, source="raydium"),
    ]
    r = reflect(records, feature_keys=["source"])
    assert len(r.patterns) == 1
    p = r.patterns[0]
    assert p.feature == "source" and p.bucket == "pumpfun"
    assert p.loss_count == 2 and p.total_count == 2
    assert p.loss_rate == 1.0


def test_reflect_top_k_limits_patterns():
    records = []
    for src in ("a", "b", "c", "d"):
        records.append(_record(f"loss-{src}", pnl=-0.1, source=src))
    r = reflect(records, feature_keys=["source"], top_k=2)
    assert len(r.patterns) == 2


def test_reflect_sorts_by_loss_count_then_avg():
    records = [
        _record("L1", pnl=-0.3, source="A"),
        _record("L2", pnl=-0.4, source="A"),
        _record("L3", pnl=-0.1, source="B"),
    ]
    r = reflect(records, feature_keys=["source"], top_k=5)
    assert r.patterns[0].bucket == "A"
    assert r.patterns[0].loss_count == 2
    assert r.patterns[1].bucket == "B"


def test_reflect_skips_features_with_no_losers():
    records = [
        _record("w1", pnl=0.20, top10_pct=0.30),
        _record("w2", pnl=0.10, top10_pct=0.20),
    ]
    r = reflect(records, feature_keys=["top10_pct"])
    assert r.patterns == []
    assert "no losses" in r.to_text().lower()


def test_reflect_infers_feature_keys_when_none_given():
    records = [
        _record("l1", pnl=-0.2, top10_pct=0.4, source="pumpfun"),
        _record("w1", pnl=0.1, top10_pct=0.2, source="raydium"),
    ]
    r = reflect(records)
    features = {p.feature for p in r.patterns}
    assert features.issubset({"top10_pct", "source"})


# -- ReflectionResult text formatting --------------------------------------


def test_to_text_includes_pattern_lines_and_losing_ids():
    r = ReflectionResult(
        window=10,
        total_decisions=10,
        total_losses=3,
        avg_loss_pnl=-0.22,
        patterns=[
            Pattern(feature="top10_pct", bucket="> 0.30",
                    loss_count=3, total_count=4, avg_pnl=-0.18),
        ],
        losing_ids=["PF26", "ILY", "X1"],
    )
    text = r.to_text()
    assert "10 decisions" in text
    assert "3 losers" in text
    assert "-22" in text  # avg pnl formatted
    assert "PF26" in text and "ILY" in text
    assert "top10_pct" in text


# -- ReflectiveNode integration --------------------------------------------


@pytest.mark.asyncio
async def test_reflective_node_writes_to_scratch():
    log = DecisionLog(InMemoryStore())
    await log.log("PF26", {"top10_pct": 0.38, "source": "pumpfun"})
    await log.record_outcome("PF26", {"pnl": -0.26})
    await log.log("ILY", {"top10_pct": 0.40, "source": "pumpfun"})
    await log.record_outcome("ILY", {"pnl": -0.21})
    await log.log("WIN", {"top10_pct": 0.10, "source": "raydium"})
    await log.record_outcome("WIN", {"pnl": 0.30})

    node = ReflectiveNode("reflect", log, feature_keys=["source"])
    state = State()
    cmd = await node.run(state)

    assert cmd is None  # ReflectiveNode never returns a Command
    result = state.scratch["lessons"]
    assert isinstance(result, ReflectionResult)
    assert result.total_losses == 2
    text = state.scratch["lessons_text"]
    assert isinstance(text, str)
    assert "pumpfun" in text
    assert "PF26" in text and "ILY" in text


@pytest.mark.asyncio
async def test_reflective_node_respects_window():
    log = DecisionLog(InMemoryStore())
    for i in range(10):
        await log.log(f"r{i}", {"source": "X"})
        await log.record_outcome(f"r{i}", {"pnl": -0.1})

    node = ReflectiveNode("reflect", log, window=3, feature_keys=["source"])
    state = State()
    await node.run(state)
    assert state.scratch["lessons"].total_decisions == 3


@pytest.mark.asyncio
async def test_reflective_node_empty_log():
    log = DecisionLog(InMemoryStore())
    node = ReflectiveNode("reflect", log)
    state = State()
    await node.run(state)
    assert state.scratch["lessons"].total_decisions == 0
    assert "No prior decisions" in state.scratch["lessons_text"]


def test_reflective_node_requires_positive_window():
    log = DecisionLog(InMemoryStore())
    with pytest.raises(ValueError):
        ReflectiveNode("reflect", log, window=0)


@pytest.mark.asyncio
async def test_reflective_node_custom_output_key():
    log = DecisionLog(InMemoryStore())
    await log.log("L", {"source": "X"})
    await log.record_outcome("L", {"pnl": -0.2})

    node = ReflectiveNode(
        "reflect", log, output_key="post_mortem", feature_keys=["source"]
    )
    state = State()
    await node.run(state)
    assert "post_mortem" in state.scratch
    assert "post_mortem_text" in state.scratch
