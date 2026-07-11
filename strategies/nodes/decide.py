"""Reject and finalize nodes that produce the final ``Decision``.

In the M8 AI-first scanner the LLM analyst owns scoring and recommendation.
``finalize`` here is a thin rule node that:

1. Reads the ``FullAnalysis`` produced by the analyst node.
2. Applies hard guardrails — sanity checks that can DOWNGRADE the LLM's
   recommendation (never upgrade). Examples: LLM said "alert" but liquidity is
   below half the minimum threshold → demote to "watch".
3. Assembles the final ``Decision`` (carrying ``analysis`` for the bot to render).

``reject`` handles the hard-gate rejection path (safety / intel / market gates).
"""

from __future__ import annotations

from collections.abc import Callable

from trading.schemas import Decision, FullAnalysis
from zetryn.analytics import CalibrationMap
from zetryn.core import State


def _latency_ms(state: State) -> float:
    return round(sum(t.duration_ms for t in state.trace), 2)


def reject(state: State) -> None:
    """Produce a skip Decision when a hard gate fails. Names the failure."""
    reasons: list[str] = []
    if not state.scratch.get("safety_ok", True):
        if state.scratch.get("rug_risk"):
            reasons.append("contract unsafe (rug risk)")
        else:
            reasons.append("holder distribution too concentrated")
    if not state.scratch.get("intel_ok", True):
        block = state.scratch.get("intel_block_reason") or "wallet intel failed"
        reasons.append(block)
    if not state.scratch.get("market_ok", True):
        reasons.append("liquidity/volume below threshold")

    state.output = Decision(
        action="skip",
        confidence=0.0,
        scores={
            k: round(state.scratch[k], 4)
            for k in ("safety_score", "market_score")
            if k in state.scratch
        },
        reasons=reasons or ["filtered"],
        flags={
            "rug_risk": bool(state.scratch.get("rug_risk", False)),
            "llm_failed": False,
            "hard_gate": True,
        },
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


def _apply_guardrails(
    analysis: FullAnalysis, state: State
) -> tuple[FullAnalysis, list[str]]:
    """Return possibly-demoted analysis + list of guardrail messages.

    Guardrails only demote (alert -> watch -> skip), never promote. They exist
    so a hallucinated bullish verdict cannot bypass hard reality.
    """
    cfg = state.context.config
    t = state.context.token
    messages: list[str] = []

    rec = analysis.recommendation

    # 1) Liquidity sanity: an alert with liquidity well below the minimum is
    #    almost always a hallucination.
    if rec == "alert" and t.market.liquidity_usd < cfg.min_liquidity_usd * 0.5:
        rec = "watch"
        messages.append("guardrail: liquidity below half of minimum, demoted to watch")

    # 2) Sniper density: an alert with a bot-dominated launch is risky.
    if rec == "alert" and t.wallets.sniper_wallet_count > cfg.max_sniper_wallets * 2:
        rec = "watch"
        messages.append("guardrail: sniper density too high, demoted to watch")

    # 3) Sell pressure: explicit alert into clear sell pressure → demote.
    a = t.activity
    total_5m = a.buys_5m + a.sells_5m
    if rec == "alert" and total_5m >= 20 and a.buy_ratio_5m < cfg.min_buy_ratio_5m:
        rec = "watch"
        messages.append(
            f"guardrail: buy ratio {a.buy_ratio_5m:.2f} below floor, demoted to watch"
        )

    # 4) Score/recommendation consistency: the recommendation must be backed
    #    by its own final_score per the configured bands. Cascades: an alert
    #    scored below the watch floor falls all the way to skip.
    if rec == "alert" and analysis.final_score < cfg.alert_threshold:
        rec = "watch"
        messages.append(
            f"guardrail: final score {analysis.final_score:.2f} below alert "
            f"threshold {cfg.alert_threshold:.2f}, demoted to watch"
        )
    if rec == "watch" and analysis.final_score < cfg.watch_threshold:
        rec = "skip"
        messages.append(
            f"guardrail: final score {analysis.final_score:.2f} below watch "
            f"threshold {cfg.watch_threshold:.2f}, demoted to skip"
        )

    if rec == analysis.recommendation:
        return analysis, messages
    return analysis.model_copy(update={"recommendation": rec}), messages


def make_finalize(
    calibration: CalibrationMap | None = None,
) -> Callable[[State], None]:
    """Build a ``finalize`` node, optionally calibrating confidence.

    With a fitted :class:`CalibrationMap`, ``Decision.confidence`` becomes the
    empirical win rate observed for scores like the analyst's ``final_score``
    (per token source when that source has enough outcome data). The raw score
    stays available in ``scores["final"]``.
    """

    def fn(state: State) -> None:
        _finalize(state, calibration)

    return fn


def finalize(state: State) -> None:
    """Convert the analyst's ``FullAnalysis`` into the final ``Decision``."""
    _finalize(state, None)


def _finalize(state: State, calibration: CalibrationMap | None) -> None:
    analysis: FullAnalysis | None = state.scratch.get("analysis")
    llm_failed = state.scratch.get("analysis__llm_failed", False)

    if analysis is None:
        # Defensive: should not happen if graph is wired correctly. Produce a
        # safe skip.
        state.output = Decision(
            action="skip",
            confidence=0.0,
            reasons=["analyst produced no output"],
            flags={"llm_failed": True},
            meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
        )
        return

    guarded, guard_msgs = _apply_guardrails(analysis, state)

    reasons = [
        f"safety {guarded.safety.verdict} ({guarded.safety.score:.2f})",
        f"market {guarded.market.verdict} ({guarded.market.score:.2f})",
        f"wallets {guarded.wallets.verdict} ({guarded.wallets.score:.2f})",
        f"social {guarded.social.verdict} ({guarded.social.score:.2f})",
    ]
    if guarded.reasoning:
        reasons.append(f"analyst: {guarded.reasoning}")
    if llm_failed:
        reasons.append("LLM unavailable; conservative skip")
    reasons.extend(guard_msgs)

    scores = {
        "safety": round(guarded.safety.score, 4),
        "market": round(guarded.market.score, 4),
        "wallets": round(guarded.wallets.score, 4),
        "social": round(guarded.social.score, 4),
        "final": round(guarded.final_score, 4),
    }

    confidence = round(guarded.final_score, 4)
    calibrated = calibration is not None and calibration.total > 0
    if calibrated:
        confidence = round(
            calibration.calibrate(
                guarded.final_score, source=state.context.token.source
            ),
            4,
        )
        scores["calibrated"] = confidence

    state.output = Decision(
        action=guarded.recommendation,
        confidence=confidence,
        scores=scores,
        reasons=reasons,
        flags={
            "rug_risk": False,
            "llm_failed": bool(llm_failed),
            "guardrail_applied": bool(guard_msgs),
            "calibrated": calibrated,
        },
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
        analysis=guarded,
    )
