"""Nodes for the Organic Growth Detector (v0.16.0 / A1).

Triage filter — classifies a token's post-launch time-series as organic,
suspicious, or manipulated. Returns a Decision with:
  action="buy"   = organic   → bot promotes scanner candidate
  action="skip"  = suspicious → bot runs normal scanner flow
  action="abort" = manipulated → bot skips and cools down

Boundary: framework reads `GrowthSnapshot` computed by the bot from its
candle/trade stream. It never fetches price data or aggregates candles.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from trading.schemas import (
    AuditVerdict,
    Decision,
    GrowthVerdict,
)
from zetryn.core import Command, State
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, Message, system, user
from zetryn.llm.structured import structured_complete

from . import sniper_nodes

fast_safety = sniper_nodes.fast_safety

_TRAJECTORY_ORGANIC = {"steady_climb", "volatile"}
_TRAJECTORY_DEAD = {"flat", "declining"}


def _latency_ms(state: State) -> float:
    return round(sum(t.duration_ms for t in state.trace), 4)


def _emit(
    state: State,
    action: str,
    classification: str,
    organic_score: float,
    confidence: float,
    reasons: list[str],
    *,
    rug_risk: bool = False,
    hard_end: bool = True,
) -> Command | None:
    state.output = Decision(
        action=action,
        confidence=round(confidence, 3),
        size=None,
        scores={"organic_score": round(organic_score, 3)},
        reasons=reasons,
        flags={
            "rug_risk": rug_risk,
            "llm_failed": False,
            "classification": classification,
        },
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )
    return Command(goto="__end__") if hard_end else None


def _abort(
    state: State,
    reason: str,
    classification: str = "manipulated",
    *,
    rug_risk: bool = False,
) -> Command:
    return _emit(
        state,
        action="abort" if classification == "manipulated" else "skip",
        classification=classification,
        organic_score=0.0,
        confidence=0.9,
        reasons=[reason],
        rug_risk=rug_risk,
    )


# -- pure-rule gates ---------------------------------------------------------


def observation_gate(state: State) -> Command | None:
    """Reject if we don't have enough history to classify reliably."""
    snap = state.context.snapshot
    cfg = state.context.config

    if snap.observation_seconds < cfg.min_observation_seconds:
        return _abort(
            state,
            f"insufficient observation: {snap.observation_seconds:.0f}s "
            f"(min {cfg.min_observation_seconds:.0f}s) — too early to classify",
            classification="suspicious",
        )
    if snap.candle_count < cfg.min_candle_count:
        return _abort(
            state,
            f"too few candles: {snap.candle_count} "
            f"(min {cfg.min_candle_count}) — need more history",
            classification="suspicious",
        )
    return None


def manipulation_gate(state: State) -> Command | None:
    """Hard abort on clear manipulation patterns — no scoring needed.

    Two hard tells:
      1. Vertical pump + zero sells: coordinated buy-only action, no
         organic sellers anywhere in the window.
      2. Whale-dominated volume beyond the hard cap: no retail
         participation at all.
    """
    snap = state.context.snapshot
    cfg = state.context.config

    if (
        snap.price_trajectory == "vertical_pump"
        and snap.sell_presence_pct < cfg.min_sell_presence_pct
    ):
        return _abort(
            state,
            f"manipulation detected: vertical_pump + zero sellers "
            f"(sell_presence={snap.sell_presence_pct:.2f} < "
            f"{cfg.min_sell_presence_pct:.2f}) — coordinated pump",
        )
    if snap.whale_volume_pct > cfg.max_whale_volume_pct + 0.20:
        # Hard abort only when extreme (20pp above the scoring threshold)
        return _abort(
            state,
            f"manipulation detected: extreme whale dominance "
            f"whale_volume={snap.whale_volume_pct:.1%} "
            f"(hard cap {cfg.max_whale_volume_pct + 0.20:.1%})",
        )
    return None


def organic_classify(state: State) -> Command:
    """Score 5 organic dimensions and emit a classification Decision.

    Each dimension contributes 0.2 to `organic_score` (max 1.0):
      1. Price trajectory is organic (steady_climb or volatile)
      2. Sell presence in the healthy band (not zero, not excessive)
      3. Unique buyer trend is non-declining
      4. A healthy pullback occurred (real demand, not just bots)
      5. Whale volume is below the dominance threshold
    """
    snap = state.context.snapshot
    cfg = state.context.config

    dim_trajectory = snap.price_trajectory in _TRAJECTORY_ORGANIC
    dim_sells = (
        cfg.min_sell_presence_pct
        <= snap.sell_presence_pct
        <= cfg.max_sell_presence_pct
    )
    dim_buyers = snap.unique_buyer_trend >= cfg.min_unique_buyer_trend
    dim_pullback = snap.has_healthy_pullback
    dim_whale = snap.whale_volume_pct <= cfg.max_whale_volume_pct

    organic_score = sum([
        0.2 if dim_trajectory else 0.0,
        0.2 if dim_sells else 0.0,
        0.2 if dim_buyers else 0.0,
        0.2 if dim_pullback else 0.0,
        0.2 if dim_whale else 0.0,
    ])

    # Build signal list for auditability
    signals: list[str] = []
    if dim_trajectory:
        signals.append(f"price_trajectory={snap.price_trajectory} ✓")
    else:
        signals.append(f"price_trajectory={snap.price_trajectory} ✗")
    if dim_sells:
        signals.append(f"sell_presence={snap.sell_presence_pct:.2f} ✓")
    else:
        signals.append(f"sell_presence={snap.sell_presence_pct:.2f} ✗")
    if dim_buyers:
        signals.append(f"buyer_trend={snap.unique_buyer_trend:+.2f} ✓")
    else:
        signals.append(f"buyer_trend={snap.unique_buyer_trend:+.2f} ✗")
    if dim_pullback:
        signals.append("healthy_pullback ✓")
    else:
        signals.append("no_healthy_pullback ✗")
    if dim_whale:
        signals.append(f"whale_volume={snap.whale_volume_pct:.1%} ✓")
    else:
        signals.append(f"whale_volume={snap.whale_volume_pct:.1%} ✗")

    if organic_score >= cfg.organic_score_threshold:
        classification = "organic"
        action = "buy"
        confidence = 0.5 + 0.5 * (organic_score - cfg.organic_score_threshold) / (1.0 - cfg.organic_score_threshold + 1e-9)
    elif organic_score >= cfg.suspicious_score_threshold:
        classification = "suspicious"
        action = "skip"
        confidence = 0.4 + 0.3 * (organic_score - cfg.suspicious_score_threshold) / (cfg.organic_score_threshold - cfg.suspicious_score_threshold + 1e-9)
    else:
        classification = "manipulated"
        action = "abort"
        confidence = 0.5 + 0.5 * (1.0 - organic_score / max(cfg.suspicious_score_threshold, 1e-9))

    reasons = [
        f"organic_score={organic_score:.2f} → {classification}",
        f"observation={snap.observation_seconds:.0f}s "
        f"trajectory={snap.price_trajectory}",
    ] + signals

    # In hybrid_audit mode, let edge routing chain to audit_dispatch
    hard_end = state.context.config.decision_mode != "hybrid_audit"
    return _emit(
        state,
        action=action,
        classification=classification,
        organic_score=organic_score,
        confidence=max(0.0, min(confidence, 1.0)),
        reasons=reasons,
        hard_end=hard_end,
    )


# -- LLM-classify / hybrid path ----------------------------------------------

_GROWTH_LESSONS_HEADER = (
    "LESSONS from recent Organic Growth Detector outcomes — use these to "
    "avoid repeating classification errors:"
)


def _lessons_block(state: State) -> Message | None:
    text = state.scratch.get("lessons_text")
    if not text or not isinstance(text, str):
        return None
    return system(f"{_GROWTH_LESSONS_HEADER}\n\n{text}")


def _growth_facts(state: State) -> str:
    t = state.context.token
    snap = state.context.snapshot
    m, h, w = t.market, t.holders, t.wallets
    return (
        f"TOKEN: {t.symbol or t.mint[:8]} ({t.name})\n"
        f"OBSERVATION: {snap.observation_seconds:.0f}s | {snap.candle_count} candles\n"
        f"PRICE PATTERN:\n"
        f"  trajectory={snap.price_trajectory} "
        f"has_pullback={snap.has_healthy_pullback} "
        f"max_drawdown={snap.max_drawdown_pct:.1%}\n"
        f"SELL PRESENCE: {snap.sell_presence_pct:.2f} "
        f"(0=no sells, 1=all candles have sells)\n"
        f"BUYER DYNAMICS:\n"
        f"  unique_buyer_trend={snap.unique_buyer_trend:+.2f} "
        f"holder_growth={snap.holder_growth_rate:.2f}/min\n"
        f"VOLUME:\n"
        f"  whale_pct={snap.whale_volume_pct:.1%} "
        f"acceleration={snap.volume_acceleration:.2f}x\n"
        f"MARKET: mcap=${m.mcap:,.0f} liq=${m.liquidity_usd:,.0f} "
        f"vol_1h=${m.volume_1h:,.0f}\n"
        f"HOLDERS: count={h.count} top10={h.top10_pct:.0%}\n"
        f"WALLETS: smart_buys={w.smart_wallet_buys} "
        f"snipers={w.sniper_wallet_count} bundlers={w.bundler_wallet_count}"
    )


def growth_prompt(state: State) -> list[Message]:
    """LLM classifier prompt for `llm` / `hybrid` modes."""
    messages: list[Message] = [
        system(
            "You are a Solana memecoin chart-pattern classifier. Analyse the "
            "token's post-launch time-series features and classify its growth "
            "pattern as:\n"
            "  organic     — steady climb with healthy pullbacks, real sellers "
            "present, rising unique buyers, no whale dominance\n"
            "  suspicious  — mixed signals: some organic tells but also red "
            "flags that need more data\n"
            "  manipulated — clear coordination tells: vertical pump with zero "
            "sells, whale-only volume, buyers not growing\n\n"
            "Return JSON: {classification, confidence, promote_scanner, "
            "signals[], reasoning}.\n"
            "promote_scanner=true means the bot should run its full scanner "
            "on this token with a confidence boost."
        ),
    ]
    lessons = _lessons_block(state)
    if lessons is not None:
        messages.append(lessons)
    messages.append(user("Fact sheet:\n" + _growth_facts(state)))
    return messages


def make_growth_prompt(
    pack: KnowledgePack | None = None,
) -> Callable[[State], list[Message]]:
    if pack is None:
        return growth_prompt
    pack_blocks = pack.system_blocks()
    if not pack_blocks:
        return growth_prompt

    def fn(state: State) -> list[Message]:
        return pack_blocks + growth_prompt(state)

    return fn


def growth_result(model: GrowthVerdict, state: State) -> Decision:
    action_map = {
        "organic": "buy",
        "suspicious": "skip",
        "manipulated": "abort",
    }
    action = action_map.get(model.classification, "skip")
    reasons: list[str] = [
        f"LLM: {model.reasoning}" if model.reasoning else "LLM classification"
    ]
    reasons.extend(f"signal: {s}" for s in model.signals)
    return Decision(
        action=action,
        confidence=model.confidence,
        size=None,
        reasons=reasons,
        flags={
            "rug_risk": False,
            "llm_failed": False,
            "classification": model.classification,
            "promote_scanner": model.promote_scanner,
        },
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


def growth_guardrail(decision: Decision | None, state: State) -> Decision:
    """Deterministic rails: force abort on dangerous contract; can only
    demote classification (organic → suspicious), never promote."""
    if decision is None:
        decision = Decision(
            action="skip",
            confidence=0.0,
            reasons=["LLM unavailable; default suspicious"],
            flags={"rug_risk": False, "llm_failed": True, "classification": "suspicious"},
            meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
        )
    if state.context.token.contract.is_dangerous:
        decision.action = "abort"
        decision.flags["rug_risk"] = True
        decision.flags["classification"] = "manipulated"
        decision.reasons.append("guardrail: forced abort on rug risk")
    # Guardrail: rule-layer caught vertical_pump+zero-sell — never let LLM override
    snap = state.context.snapshot
    cfg = state.context.config
    if (
        snap.price_trajectory == "vertical_pump"
        and snap.sell_presence_pct < cfg.min_sell_presence_pct
        and decision.action != "abort"
    ):
        decision.action = "abort"
        decision.flags["classification"] = "manipulated"
        decision.reasons.append(
            "guardrail: vertical_pump + zero-sell overrides LLM organic verdict"
        )
    return decision


# -- hybrid_audit: async LLM second opinion ---------------------------------


def _audit_prompt(state: State) -> list[Message]:
    d: Decision = state.output
    return [
        system(
            "You are a growth-classification auditor. A rule-based classifier "
            "assessed this token's time-series. Do you AGREE? "
            "Return JSON: {agrees, confidence, concerns[], reasoning}."
        ),
        user(
            f"CLASSIFICATION: action={d.action} "
            f"classification={d.flags.get('classification')} "
            f"organic_score={d.scores.get('organic_score')}\n"
            f"Reasons: {d.reasons}\n\n"
            + _growth_facts(state)
        ),
    ]


async def _run_audit(
    client: LLMClient, messages: list[Message], model: str | None
) -> AuditVerdict:
    try:
        return await structured_complete(client, messages, AuditVerdict, model=model)
    except Exception as exc:  # noqa: BLE001
        return AuditVerdict(
            agrees=False,
            confidence=0.0,
            concerns=[f"audit_failed: {type(exc).__name__}"],
            reasoning=str(exc)[:200],
        )


def make_audit_dispatch(
    client: LLMClient,
    *,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
):
    pack_blocks: list[Message] = (
        knowledge_pack.system_blocks() if knowledge_pack is not None else []
    )

    def audit_dispatch(state: State) -> None:
        # Audit all classifications — both promotions and demotions are worth auditing
        if state.output is None:
            state.scratch["audit_skipped"] = True
            return
        base = _audit_prompt(state)
        messages = pack_blocks + base if pack_blocks else base
        task = asyncio.create_task(_run_audit(client, messages, model))
        state.scratch["audit_task"] = task
        state.output.flags["audit_dispatched"] = True

    audit_dispatch.__name__ = "audit_dispatch"
    return audit_dispatch
