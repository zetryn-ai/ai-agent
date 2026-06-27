"""Nodes for the Smart Money Confluence strategy (v0.14.0 / S5).

Fires when ≥ N pre-vetted smart wallets have accumulated the same token
within a rolling window. The bot builds and passes a `ConfluenceEvent`;
the framework validates thresholds, quality-gates each wallet, evaluates
token structure, sizes, and returns a `Decision`.

Boundary: framework reads the event and enriched `TokenInput` that the bot
fills (from Cielo/GMGN/Helius wallet feeds + DEX data) and returns a
`Decision`. It never subscribes, aggregates wallets, or executes trades.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from trading.schemas import (
    AuditVerdict,
    ConfluenceVerdict,
    Decision,
    SmartWalletProfile,
)
from zetryn.core import Command, State
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, Message, system, user
from zetryn.llm.structured import structured_complete

from . import sniper_nodes  # fast_safety re-export

fast_safety = sniper_nodes.fast_safety

_TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}


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


def make_confluence_gate(registry: "SmartWalletRegistry | None" = None):  # type: ignore[name-defined]  # noqa: F821
    """Factory: binds an optional `SmartWalletRegistry` to the gate node.

    When `registry` is provided, each accumulation's wallet is checked
    against the whitelist (tier, hit_rate, min_sol_to_copy) before being
    counted. When `registry` is None, the gate falls back to
    `ConfluenceConfig` floors only (no whitelist).

    Gate order:
      1. At least one accumulation present.
      2. Most-recent accumulation is fresh (`max_signal_age_seconds`).
      3. Per-wallet quality: tier, hit_rate, sol_amount (uses registry if
         provided, otherwise config floors directly).
      4. Unique qualifying wallet count ≥ `min_wallet_count`.

    Stores qualifying profiles in `state.scratch["qualifying_profiles"]`
    for the sizing node.
    """

    def confluence_gate(state: State) -> Command | None:
        ev = state.context.event
        cfg = state.context.config

        if not ev.accumulations:
            return _abort(state, "no accumulations in event")

        # signal freshness — check the most recent accumulation
        most_recent_age = min(a.block_age_seconds for a in ev.accumulations)
        if most_recent_age > cfg.max_signal_age_seconds:
            return _abort(
                state,
                f"most recent accumulation is {most_recent_age:.1f}s old "
                f"(max {cfg.max_signal_age_seconds:.0f}s)",
            )

        # per-wallet quality filter — deduplicate by wallet address
        seen: dict[str, SmartWalletProfile] = {}
        tier_floor = _TIER_ORDER.get(cfg.min_tier, 99)

        for acc in ev.accumulations:
            if acc.wallet in seen:
                continue  # already counted this wallet
            if acc.sol_amount < cfg.min_sol_per_wallet:
                continue  # bet too small

            # If we have a registry, look up the profile there.
            if registry is not None:
                profile = registry.get(acc.wallet)
                if profile is None:
                    continue  # not on whitelist
                if not registry.passes_global_floor(profile):
                    continue  # below pack-wide floor
            else:
                # Fallback: fabricate a minimal profile from config floors
                profile = SmartWalletProfile(
                    hit_rate=cfg.min_hit_rate,
                    tier=cfg.min_tier,
                )

            # Per-deployment floors
            wallet_tier = _TIER_ORDER.get(profile.tier, 99)
            if wallet_tier > tier_floor:
                continue
            if profile.hit_rate < cfg.min_hit_rate:
                continue
            if acc.sol_amount < profile.min_sol_to_copy:
                continue

            seen[acc.wallet] = profile

        unique_count = len(seen)
        if unique_count < cfg.min_wallet_count:
            return _abort(
                state,
                f"only {unique_count} qualifying smart wallets "
                f"(min {cfg.min_wallet_count})",
            )

        # Store for downstream sizing node
        state.scratch["qualifying_profiles"] = seen
        state.scratch["unique_wallet_count"] = unique_count
        return None

    confluence_gate.__name__ = "confluence_gate"
    return confluence_gate


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
    if cfg.min_volume_1h > 0 and m.volume_1h < cfg.min_volume_1h:
        return _abort(
            state,
            f"volume_1h ${m.volume_1h:,.0f} below min "
            f"${cfg.min_volume_1h:,.0f}",
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

    Sizing formula:
        wallet_mult   = clamp(unique_count / min_wallet_count, 1.0, 2.0)
        avg_hit_rate  = mean(profile.hit_rate for qualifying wallets)
        quality_mult  = 0.6 + 0.4 * clamp((avg_hit_rate - 0.35) / 0.35, 0, 1)
        top10_penalty = 1 - max(0, top10_pct - 0.2)
        size          = clamp(base × wallet_mult × quality_mult × top10_penalty, 0, max)
    """
    cfg = state.context.config
    h = state.context.token.holders

    profiles: dict[str, SmartWalletProfile] = state.scratch.get(
        "qualifying_profiles", {}
    )
    unique_count: int = state.scratch.get("unique_wallet_count", len(profiles))

    wallet_mult = max(1.0, min(unique_count / max(cfg.min_wallet_count, 1), 2.0))

    if profiles:
        avg_hit_rate = sum(p.hit_rate for p in profiles.values()) / len(profiles)
    else:
        avg_hit_rate = cfg.min_hit_rate

    quality_raw = (avg_hit_rate - 0.35) / max(0.35, 1e-9)
    quality_mult = 0.6 + 0.4 * max(0.0, min(quality_raw, 1.0))

    top10_penalty = max(0.0, min(1.0, 1.0 - max(0.0, h.top10_pct - 0.2)))

    size = cfg.base_size * wallet_mult * quality_mult * top10_penalty
    size = max(0.0, min(size, cfg.max_size))

    confidence = round(0.5 + 0.3 * (wallet_mult - 1.0) + 0.2 * (quality_mult - 0.6) / 0.4, 3)
    confidence = max(0.0, min(confidence, 1.0))

    state.output = Decision(
        action="buy",
        confidence=confidence,
        size=round(size, 4),
        scores={
            "wallet_mult": round(wallet_mult, 3),
            "avg_hit_rate": round(avg_hit_rate, 3),
            "quality_mult": round(quality_mult, 3),
            "top10_penalty": round(top10_penalty, 3),
        },
        reasons=[
            "pure-rule smart money confluence entry",
            f"{unique_count} qualifying wallets (min {cfg.min_wallet_count})",
            f"size {size:.4f} (cap {cfg.max_size})",
            f"wallet_mult {wallet_mult:.2f} × quality_mult {quality_mult:.2f} "
            f"× top10_penalty {top10_penalty:.2f}",
        ],
        flags={"rug_risk": False, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )


# -- LLM-decide / hybrid path ------------------------------------------------

_CONFLUENCE_LESSONS_HEADER = (
    "LESSONS from recent Smart Money Confluence outcomes — use these to avoid "
    "repeating losing patterns. The agent ran on the same data sources "
    "and these are real outcomes:"
)


def _lessons_block(state: State) -> Message | None:
    text = state.scratch.get("lessons_text")
    if not text or not isinstance(text, str):
        return None
    return system(f"{_CONFLUENCE_LESSONS_HEADER}\n\n{text}")


def _confluence_facts(state: State) -> str:
    t = state.context.token
    ev = state.context.event
    m, h, c, w = t.market, t.holders, t.contract, t.wallets

    profiles: dict[str, SmartWalletProfile] = state.scratch.get(
        "qualifying_profiles", {}
    )
    unique_count: int = state.scratch.get("unique_wallet_count", len(profiles))
    avg_hit_rate = (
        sum(p.hit_rate for p in profiles.values()) / len(profiles)
        if profiles else 0.0
    )
    total_sol = sum(
        a.sol_amount for a in ev.accumulations
        if a.wallet in profiles
    )
    tier_dist = {}
    for p in profiles.values():
        tier_dist[p.tier] = tier_dist.get(p.tier, 0) + 1

    return (
        f"TOKEN: {t.symbol or t.mint[:8]} ({t.name})\n"
        f"CONFLUENCE:\n"
        f"  qualifying_wallets={unique_count} total_sol={total_sol:.1f} "
        f"window={ev.window_seconds/3600:.1f}h\n"
        f"  avg_hit_rate={avg_hit_rate:.2f} "
        f"tier_distribution={tier_dist}\n"
        f"MARKET: mcap=${m.mcap:,.0f} liq=${m.liquidity_usd:,.0f} "
        f"vol_1h=${m.volume_1h:,.0f}\n"
        f"HOLDERS: count={h.count} top10={h.top10_pct:.0%} dev={h.dev_pct:.0%}\n"
        f"CONTRACT: bundled={c.bundled_supply} dev_rug={c.dev_rug_history} "
        f"lp_burned={c.lp_burned} lp_locked={c.lp_locked}\n"
        f"WALLETS: smart_buys={w.smart_wallet_buys} "
        f"snipers={w.sniper_wallet_count} bundlers={w.bundler_wallet_count}"
    )


def confluence_prompt(state: State) -> list[Message]:
    """Analyst prompt for `llm` / `hybrid` modes."""
    messages: list[Message] = [
        system(
            "You are a Solana smart-money confluence decider. Multiple pre-vetted "
            "smart wallets have accumulated the same token in a rolling window. "
            "The token has passed safety + rule gates. Your job: decide buy / "
            "skip / abort and a size fraction, weighing wallet quality, "
            "confluence strength (count and total SOL), and the token's "
            "on-chain structure. Strong confluence from high-tier wallets = "
            "size up; low count or poor market structure = size down or skip."
        ),
    ]
    lessons = _lessons_block(state)
    if lessons is not None:
        messages.append(lessons)
    messages.append(user("Fact sheet:\n" + _confluence_facts(state)))
    return messages


def make_confluence_prompt(
    pack: KnowledgePack | None = None,
) -> Callable[[State], list[Message]]:
    if pack is None:
        return confluence_prompt
    pack_blocks = pack.system_blocks()
    if not pack_blocks:
        return confluence_prompt

    def fn(state: State) -> list[Message]:
        return pack_blocks + confluence_prompt(state)

    return fn


def confluence_result(model: ConfluenceVerdict, state: State) -> Decision:
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


def confluence_guardrail(decision: Decision | None, state: State) -> Decision:
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
            "You are a smart-money confluence auditor. A rule-based bot has "
            "decided on a token with multi-wallet accumulation. Your job: do "
            "you AGREE? Return JSON: {agrees, confidence, concerns[], "
            "reasoning}. Be honest — this audit informs future rule tuning, "
            "not this trade."
        ),
        user(
            f"DECISION: action={d.action} size={d.size} "
            f"confidence={d.confidence}\n"
            f"Reasons: {d.reasons}\n\n"
            + _confluence_facts(state)
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
