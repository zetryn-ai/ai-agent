"""Nodes for the Pump.fun graduation snipe strategy (v0.12.0).

Mirrors the sniper's structure: pure-rule gates that can abort fast, an LLM
decider for ``llm`` / ``hybrid`` modes (with optional reflective loop), and
an audit-dispatch node for ``hybrid_audit`` mode.

Boundary: the framework reads ``GraduationEvent`` + enriched ``TokenInput``
that the bot fills (from Pump.fun WS + Raydium/Helius) and returns a
``Decision``. It never subscribes, fetches, or executes.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from trading.schemas import (
    AuditVerdict,
    Decision,
    GraduationVerdict,
)
from zetryn.core import Command, State
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, Message, system, user
from zetryn.llm.structured import structured_complete

# `fast_safety` is identical to the sniper's contract check — reuse it.
from . import sniper_nodes  # re-export `sniper_nodes.fast_safety`

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


def graduation_gate(state: State) -> Command | None:
    """Bonding-curve + pair structure checks.

    Order matches the spec. Each rejection writes a precise ``Decision`` so
    the bot can log exactly which gate fired.
    """
    ev = state.context.event
    cfg = state.context.config

    if cfg.require_lp_burned and ev.lp_burned is False:
        return _abort(state, "LP not burned at graduation", action="abort", rug_risk=True)
    if ev.pair_age_seconds > cfg.max_pair_age_seconds:
        return _abort(
            state,
            f"pair_age {ev.pair_age_seconds:.1f}s > max {cfg.max_pair_age_seconds:.1f}s "
            "(detected too late)",
        )
    if ev.bonding_curve_fill_seconds > cfg.max_fill_seconds:
        return _abort(
            state,
            f"bonding curve fill {ev.bonding_curve_fill_seconds:.0f}s > "
            f"max {cfg.max_fill_seconds:.0f}s (weak demand)",
        )
    if ev.bonding_curve_unique_buyers < cfg.min_unique_buyers:
        return _abort(
            state,
            f"unique_buyers {ev.bonding_curve_unique_buyers} < "
            f"min {cfg.min_unique_buyers}",
        )
    if ev.initial_liquidity_sol < cfg.min_initial_liquidity_sol:
        return _abort(
            state,
            f"initial_liquidity {ev.initial_liquidity_sol:.1f} SOL < "
            f"min {cfg.min_initial_liquidity_sol:.1f}",
        )
    if ev.bonding_curve_premium_pct > cfg.max_premium_pct:
        return _abort(
            state,
            f"premium {ev.bonding_curve_premium_pct:.1f}% > "
            f"max {cfg.max_premium_pct:.1f}% (already pumped)",
        )
    return None


def market_gate(state: State) -> Command | None:
    """Standard token-quality checks on the enriched ``TokenInput``.

    Mirrors the sniper / KOL market_gate style.
    """
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
    if cfg.min_volume_1h > 0 and m.volume_1h < cfg.min_volume_1h:
        return _abort(
            state,
            f"volume_1h ${m.volume_1h:,.0f} below min ${cfg.min_volume_1h:,.0f}",
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
    """Deterministic sizing → buy Decision (terminal rule node)."""
    cfg = state.context.config
    ev = state.context.event
    h = state.context.token.holders

    # Reward strong demand: shorter fills + more unique buyers ⇒ closer to max.
    fill_ratio = max(0.0, min(1.0, 1.0 - (ev.bonding_curve_fill_seconds / max(cfg.max_fill_seconds, 1.0))))
    buyer_ratio = max(0.0, min(1.0, ev.bonding_curve_unique_buyers / max(cfg.min_unique_buyers * 3.0, 1.0)))
    demand_mult = 0.6 + 0.4 * ((fill_ratio + buyer_ratio) / 2)  # 0.6..1.0

    concentration_penalty = max(0.0, h.top10_pct - 0.2)
    size = cfg.base_size * demand_mult * (1.0 - concentration_penalty)
    size = max(0.0, min(size, cfg.max_size))

    state.output = Decision(
        action="buy",
        confidence=round(0.5 + 0.5 * demand_mult, 3),
        size=round(size, 4),
        scores={
            "fill_ratio": round(fill_ratio, 3),
            "buyer_ratio": round(buyer_ratio, 3),
            "demand_mult": round(demand_mult, 3),
        },
        reasons=[
            "pure-rule graduation entry",
            f"size {size:.4f} (cap {cfg.max_size})",
            f"fill {ev.bonding_curve_fill_seconds:.0f}s buyers={ev.bonding_curve_unique_buyers}",
        ],
        flags={"rug_risk": False, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


# -- LLM-decide / hybrid path ------------------------------------------------


_GRAD_LESSONS_HEADER = (
    "LESSONS from recent graduation snipe outcomes — use these to avoid "
    "repeating losing patterns. The agent ran on the same data sources "
    "and these are real outcomes:"
)


def _grad_lessons_block(state: State) -> Message | None:
    text = state.scratch.get("lessons_text")
    if not text or not isinstance(text, str):
        return None
    return system(f"{_GRAD_LESSONS_HEADER}\n\n{text}")


def _grad_facts(state: State) -> str:
    t = state.context.token
    ev = state.context.event
    m, h, c, w = t.market, t.holders, t.contract, t.wallets
    return (
        f"TOKEN: {t.symbol or t.mint[:8]} ({t.name})\n"
        f"GRADUATION EVENT:\n"
        f"  pair_age={ev.pair_age_seconds:.1f}s "
        f"detected_at={ev.detected_at_ts:.0f}\n"
        f"  bonding_curve: fill={ev.bonding_curve_fill_seconds:.0f}s "
        f"unique_buyers={ev.bonding_curve_unique_buyers} "
        f"sol_raised={ev.bonding_curve_sol_raised:.1f} "
        f"premium={ev.bonding_curve_premium_pct:+.1f}%\n"
        f"  raydium: initial_liq_sol={ev.initial_liquidity_sol:.1f} "
        f"initial_token_pct={ev.initial_liquidity_token_pct:.1f}% "
        f"lp_burned={ev.lp_burned}\n"
        f"MARKET: mcap=${m.mcap:,.0f} liq=${m.liquidity_usd:,.0f} "
        f"vol_1h=${m.volume_1h:,.0f}\n"
        f"HOLDERS: count={h.count} top10={h.top10_pct:.0%} dev={h.dev_pct:.0%}\n"
        f"CONTRACT: bundled={c.bundled_supply} dev_rug={c.dev_rug_history} "
        f"lp_burned={c.lp_burned} lp_locked={c.lp_locked}\n"
        f"WALLETS: smart_buys={w.smart_wallet_buys} "
        f"snipers={w.sniper_wallet_count} bundlers={w.bundler_wallet_count}"
    )


def graduation_prompt(state: State) -> list[Message]:
    """Build the analyst prompt for ``llm`` / ``hybrid`` modes."""
    messages: list[Message] = [
        system(
            "You are a Solana graduation-snipe decider. A Pump.fun token just "
            "graduated to Raydium. The token has already passed safety + rule "
            "gates. Your job: decide buy / skip / abort and a size fraction, "
            "weighing bonding-curve demand quality (fill time, unique buyers), "
            "LP setup, and the token's broader on-chain structure. "
            "Be decisive — the entry window is short."
        ),
    ]
    lessons = _grad_lessons_block(state)
    if lessons is not None:
        messages.append(lessons)
    messages.append(user("Fact sheet:\n" + _grad_facts(state)))
    return messages


def make_graduation_prompt(
    pack: KnowledgePack | None = None,
) -> Callable[[State], list[Message]]:
    if pack is None:
        return graduation_prompt
    pack_blocks = pack.system_blocks()
    if not pack_blocks:
        return graduation_prompt

    def fn(state: State) -> list[Message]:
        return pack_blocks + graduation_prompt(state)

    return fn


def graduation_result(model: GraduationVerdict, state: State) -> Decision:
    cfg = state.context.config
    size = max(0.0, min(model.size_pct * cfg.max_size, cfg.max_size))
    action = model.action if model.action in {"buy", "skip", "abort"} else "skip"
    reasons: list[str] = [f"LLM: {model.reasoning}" if model.reasoning else "LLM decision"]
    reasons.extend(f"concern: {c}" for c in model.concerns)
    return Decision(
        action=action,
        confidence=model.confidence,
        size=round(size, 4) if action == "buy" else None,
        reasons=reasons,
        flags={"rug_risk": False, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


def graduation_guardrail(decision: Decision | None, state: State) -> Decision:
    """Deterministic rails the LLM cannot breach (hybrid mode)."""
    cfg = state.context.config
    ev = state.context.event
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
    if cfg.require_lp_burned and ev.lp_burned is False:
        decision.action = "abort"
        decision.size = None
        decision.flags["rug_risk"] = True
        decision.reasons.append("guardrail: forced abort — LP not burned")
    if decision.size is not None and decision.size > cfg.max_size:
        decision.size = cfg.max_size
        decision.reasons.append(f"guardrail: size capped at {cfg.max_size}")
    return decision


# -- hybrid_audit: async LLM second opinion ---------------------------------


def _audit_prompt(state: State) -> list[Message]:
    d: Decision = state.output
    return [
        system(
            "You are a graduation-snipe auditor. A rule-based bot has just "
            "decided on a freshly graduated Pump.fun token. Your job: do you "
            "AGREE with the decision? Return JSON: {agrees, confidence, "
            "concerns[], reasoning}. Be honest — this audit informs future "
            "rule tuning, not this trade."
        ),
        user(
            f"DECISION: action={d.action} size={d.size} confidence={d.confidence}\n"
            f"Reasons: {d.reasons}\n\n"
            + _grad_facts(state)
        ),
    ]


async def _run_audit(
    client: LLMClient, messages: list[Message], model: str | None
) -> AuditVerdict:
    try:
        return await structured_complete(client, messages, AuditVerdict, model=model)
    except Exception as exc:  # noqa: BLE001 — bg task must not propagate
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
