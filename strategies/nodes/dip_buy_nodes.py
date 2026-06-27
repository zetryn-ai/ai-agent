"""Nodes for the Early-Stage Dip Buy strategy (v0.15.0 / S6).

Fires after an initial post-launch or post-graduation dump settles. The
bot monitors the token's price action, computes sell-pressure and recovery
metrics, and pushes a `DipBuyContext` per candidate entry window. The
framework validates timing, dip depth, recovery signals, and token quality,
then sizes and returns a `Decision`.

Boundary: framework reads the `DipBuySnapshot` and enriched `TokenInput`
that the bot fills (from its Helius/Cielo/GMGN monitoring). It never
aggregates candles, tracks price history, or executes.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from trading.schemas import (
    AuditVerdict,
    Decision,
    DipBuyVerdict,
)
from zetryn.core import Command, State
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, Message, system, user
from zetryn.llm.structured import structured_complete

from . import sniper_nodes

fast_safety = sniper_nodes.fast_safety


def _latency_ms(state: State) -> float:
    return round(sum(t.duration_ms for t in state.trace), 4)


def _abort(
    state: State,
    reason: str,
    *,
    action: str = "skip",
    rug_risk: bool = False,
) -> Command:
    state.output = Decision(
        action=action,
        confidence=0.0,
        reasons=[reason],
        flags={"rug_risk": rug_risk, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )
    return Command(goto="__end__")


# -- pure-rule gates ---------------------------------------------------------


def timing_gate(state: State) -> Command | None:
    """Validate that the snapshot falls inside the allowed timing window.

    Too early → dump wave is still live, not settled yet.
    Too late  → entry window has closed, price has recovered or died.
    """
    snap = state.context.snapshot
    cfg = state.context.config

    if snap.time_since_event_seconds < cfg.min_time_since_event_seconds:
        return _abort(
            state,
            f"too early: {snap.time_since_event_seconds:.0f}s since "
            f"{snap.event_type} (min {cfg.min_time_since_event_seconds:.0f}s) "
            "— dump wave still live",
        )
    if snap.time_since_event_seconds > cfg.max_time_since_event_seconds:
        return _abort(
            state,
            f"too late: {snap.time_since_event_seconds:.0f}s since "
            f"{snap.event_type} (max {cfg.max_time_since_event_seconds:.0f}s) "
            "— entry window closed",
        )
    return None


def dip_gate(state: State) -> Command | None:
    """Check that a real dip occurred and sell pressure has subsided.

    A valid dip entry needs:
      1. Price actually dropped from the post-event ATH (min_dip_pct).
      2. Current sell pressure is below threshold — the dump is calming.
    """
    snap = state.context.snapshot
    cfg = state.context.config

    actual_dip = -snap.price_vs_ath_pct  # positive when below ATH
    if actual_dip < cfg.min_dip_pct:
        return _abort(
            state,
            f"insufficient dip: {actual_dip:.1%} below ATH "
            f"(min {cfg.min_dip_pct:.1%}) — no meaningful dump to buy",
        )
    if snap.sell_pressure_score > cfg.max_sell_pressure_score:
        return _abort(
            state,
            f"sell pressure still high: {snap.sell_pressure_score:.2f} "
            f"(max {cfg.max_sell_pressure_score:.2f}) — dump not settled",
        )
    return None


def recovery_gate(state: State) -> Command | None:
    """Check that recovery signals are present.

    All four must pass — these are the positive confirmation that the
    dump has ended and buyers are returning:
      1. Buy ratio improving (buys overtaking sells).
      2. Holder retention (organic holders stayed through the dump).
      3. Unique buyers not falling (flat or rising).
      4. Price not making new lows (stable floor).
    """
    snap = state.context.snapshot
    cfg = state.context.config

    if snap.buy_ratio_5m < cfg.min_buy_ratio_5m:
        return _abort(
            state,
            f"buy_ratio_5m {snap.buy_ratio_5m:.2f} below min "
            f"{cfg.min_buy_ratio_5m:.2f} — sellers still dominating",
        )
    if snap.holder_retention_pct < cfg.min_holder_retention_pct:
        return _abort(
            state,
            f"holder_retention {snap.holder_retention_pct:.1%} below min "
            f"{cfg.min_holder_retention_pct:.1%} — too many holders sold",
        )
    if snap.unique_buyers_trend < cfg.min_unique_buyers_trend:
        return _abort(
            state,
            f"unique_buyers_trend {snap.unique_buyers_trend:.2f} below min "
            f"{cfg.min_unique_buyers_trend:.2f} — new buyers not entering",
        )
    if snap.price_stable_seconds < cfg.min_price_stable_seconds:
        return _abort(
            state,
            f"price_stable_seconds {snap.price_stable_seconds:.0f}s below min "
            f"{cfg.min_price_stable_seconds:.0f}s — price still declining",
        )
    return None


def market_gate(state: State) -> Command | None:
    """Standard token-quality checks on the enriched `TokenInput`."""
    t = state.context.token
    cfg = state.context.config
    m = t.market
    h = t.holders
    w = t.wallets

    if m.liquidity_usd < cfg.min_liquidity_usd:
        return _abort(
            state,
            f"liquidity ${m.liquidity_usd:,.0f} below min "
            f"${cfg.min_liquidity_usd:,.0f}",
        )
    if h.top10_pct > cfg.max_top10_pct:
        return _abort(
            state,
            f"top10_pct {h.top10_pct:.0%} above max {cfg.max_top10_pct:.0%}",
        )
    if w.bundler_wallet_count > cfg.max_bundler_wallets:
        return _abort(
            state,
            f"bundler_count {w.bundler_wallet_count} above max "
            f"{cfg.max_bundler_wallets}",
        )
    if w.sniper_wallet_count > cfg.max_sniper_wallets:
        return _abort(
            state,
            f"sniper_count {w.sniper_wallet_count} above max "
            f"{cfg.max_sniper_wallets}",
        )
    return None


def rule_size_and_buy(state: State) -> None:
    """Deterministic sizing → buy Decision (terminal rule node).

    Formula (from spec):
        recovery_score  = mean(buy_ratio_5m, holder_retention, (trend+1)/2)
        dip_bonus       = clamp((|dip| - min_dip) / 0.30, 0, 1)
        sell_calm       = 1 - sell_pressure_score
        size            = clamp(base × recovery × (1 + 0.5 × dip_bonus) × sell_calm, 0, max)
    """
    snap = state.context.snapshot
    cfg = state.context.config

    recovery_score = (
        snap.buy_ratio_5m
        + snap.holder_retention_pct
        + (snap.unique_buyers_trend + 1.0) / 2.0
    ) / 3.0

    actual_dip = -snap.price_vs_ath_pct
    dip_bonus = max(0.0, min((actual_dip - cfg.min_dip_pct) / 0.30, 1.0))

    sell_calm = 1.0 - snap.sell_pressure_score

    size = cfg.base_size * recovery_score * (1.0 + 0.5 * dip_bonus) * sell_calm
    size = max(0.0, min(size, cfg.max_size))

    confidence = round(
        0.4 * recovery_score + 0.3 * (1.0 - snap.sell_pressure_score) + 0.3 * dip_bonus,
        3,
    )

    state.output = Decision(
        action="buy",
        confidence=max(0.0, min(confidence, 1.0)),
        size=round(size, 4),
        scores={
            "recovery_score": round(recovery_score, 3),
            "dip_bonus": round(dip_bonus, 3),
            "sell_calm": round(sell_calm, 3),
        },
        reasons=[
            f"pure-rule dip-buy ({snap.event_type})",
            f"dip {actual_dip:.1%} below ATH "
            f"({snap.time_since_event_seconds:.0f}s since event)",
            f"recovery: buy_ratio={snap.buy_ratio_5m:.2f} "
            f"retention={snap.holder_retention_pct:.1%} "
            f"buyers_trend={snap.unique_buyers_trend:+.2f}",
            f"size {size:.4f} (cap {cfg.max_size})",
        ],
        flags={"rug_risk": False, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


# -- LLM-decide / hybrid path ------------------------------------------------

_DIP_LESSONS_HEADER = (
    "LESSONS from recent Early-Stage Dip Buy outcomes — use these to avoid "
    "repeating losing patterns. The agent ran on the same data sources "
    "and these are real outcomes:"
)


def _lessons_block(state: State) -> Message | None:
    text = state.scratch.get("lessons_text")
    if not text or not isinstance(text, str):
        return None
    return system(f"{_DIP_LESSONS_HEADER}\n\n{text}")


def _dip_facts(state: State) -> str:
    t = state.context.token
    snap = state.context.snapshot
    m, h, c, w = t.market, t.holders, t.contract, t.wallets
    return (
        f"TOKEN: {t.symbol or t.mint[:8]} ({t.name})\n"
        f"EVENT: {snap.event_type} | {snap.time_since_event_seconds:.0f}s ago\n"
        f"DIP METRICS:\n"
        f"  price_vs_ath={snap.price_vs_ath_pct:+.1%} "
        f"sell_pressure={snap.sell_pressure_score:.2f}\n"
        f"RECOVERY SIGNALS:\n"
        f"  buy_ratio_5m={snap.buy_ratio_5m:.2f} "
        f"holder_retention={snap.holder_retention_pct:.1%} "
        f"buyers_trend={snap.unique_buyers_trend:+.2f} "
        f"price_stable={snap.price_stable_seconds:.0f}s\n"
        f"MARKET: mcap=${m.mcap:,.0f} liq=${m.liquidity_usd:,.0f} "
        f"vol_1h=${m.volume_1h:,.0f}\n"
        f"HOLDERS: count={h.count} top10={h.top10_pct:.0%} dev={h.dev_pct:.0%}\n"
        f"CONTRACT: bundled={c.bundled_supply} dev_rug={c.dev_rug_history} "
        f"lp_burned={c.lp_burned}\n"
        f"WALLETS: smart_buys={w.smart_wallet_buys} "
        f"snipers={w.sniper_wallet_count} bundlers={w.bundler_wallet_count}"
    )


def dip_prompt(state: State) -> list[Message]:
    """Analyst prompt for `llm` / `hybrid` modes."""
    messages: list[Message] = [
        system(
            "You are a Solana early-stage dip-buy analyst. A token has "
            "just experienced a post-launch or post-graduation dump and "
            "the rule layer detected a possible settlement. The token has "
            "already passed safety + timing + dip depth + recovery gates. "
            "Your job: assess whether this is a genuine recovery entry or a "
            "dead-cat bounce. Weigh holder retention (organic buyers held), "
            "buy-ratio recovery (demand returning), sell pressure (dump over?), "
            "and token quality. Be decisive — the entry window is short."
        ),
    ]
    lessons = _lessons_block(state)
    if lessons is not None:
        messages.append(lessons)
    messages.append(user("Fact sheet:\n" + _dip_facts(state)))
    return messages


def make_dip_prompt(
    pack: KnowledgePack | None = None,
) -> Callable[[State], list[Message]]:
    if pack is None:
        return dip_prompt
    pack_blocks = pack.system_blocks()
    if not pack_blocks:
        return dip_prompt

    def fn(state: State) -> list[Message]:
        return pack_blocks + dip_prompt(state)

    return fn


def dip_result(model: DipBuyVerdict, state: State) -> Decision:
    cfg = state.context.config
    size = max(0.0, min(model.size_pct * cfg.max_size, cfg.max_size))
    action = model.action if model.action in {"buy", "skip", "abort"} else "skip"
    reasons: list[str] = [
        f"LLM: {model.reasoning}" if model.reasoning else "LLM decision"
    ]
    reasons.extend(f"concern: {c}" for c in model.concerns)
    return Decision(
        action=action,
        confidence=model.confidence,
        size=round(size, 4) if action == "buy" else None,
        reasons=reasons,
        flags={"rug_risk": False, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


def dip_guardrail(decision: Decision | None, state: State) -> Decision:
    """Deterministic rails the LLM cannot breach (hybrid mode)."""
    cfg = state.context.config
    if decision is None:
        decision = Decision(
            action="skip",
            confidence=0.0,
            reasons=["LLM unavailable; conservative skip"],
            flags={"rug_risk": False, "llm_failed": True},
            meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
        )
    if state.context.token.contract.is_dangerous:
        decision.action = "abort"
        decision.size = None
        decision.flags["rug_risk"] = True
        decision.reasons.append("guardrail: forced abort on rug risk")
    if decision.size is not None and decision.size > cfg.max_size:
        decision.size = cfg.max_size
        decision.reasons.append(f"guardrail: size capped at {cfg.max_size}")
    return decision


# -- hybrid_audit: async LLM second opinion ---------------------------------


def _audit_prompt(state: State) -> list[Message]:
    d: Decision = state.output
    return [
        system(
            "You are a dip-buy auditor. A rule-based bot decided on a "
            "post-event dip entry. Your job: do you AGREE? Return JSON: "
            "{agrees, confidence, concerns[], reasoning}. Be honest — "
            "this audit informs future rule tuning, not this trade."
        ),
        user(
            f"DECISION: action={d.action} size={d.size} "
            f"confidence={d.confidence}\n"
            f"Reasons: {d.reasons}\n\n"
            + _dip_facts(state)
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
        if state.output is None or state.output.action not in {"buy"}:
            state.scratch["audit_skipped"] = True
            return
        base = _audit_prompt(state)
        messages = pack_blocks + base if pack_blocks else base
        task = asyncio.create_task(_run_audit(client, messages, model))
        state.scratch["audit_task"] = task
        state.output.flags["audit_dispatched"] = True

    audit_dispatch.__name__ = "audit_dispatch"
    return audit_dispatch
