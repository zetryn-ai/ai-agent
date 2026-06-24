"""Deterministic rule nodes for the scanner.

Each reads the pushed ``TokenInput`` from the context, writes a per-dimension score
plus a boolean gate flag into ``scratch``, and lets the graph's edges route. Fast
and free (no LLM), so they drop the bulk of junk before any LLM call.

Dimensions: safety (contract + holder concentration), market (liquidity + volume),
social (twitter + telegram alpha + KOL), wallets (smart money / bundler / sniper
density), momentum (short-window buy pressure). Narrative (LLM) is a separate node.

Hard gates (abort fast, save LLM): ``intel_gate`` (bundle/dev rug/RugCheck floor)
and the existing ``safety_gate`` / ``market_gate``.
"""

from __future__ import annotations

from zetryn.core import State


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def safety_gate(state: State) -> None:
    """Contract safety + holder concentration. Hard gate against rugs."""
    ctx = state.context
    c = ctx.token.contract
    h = ctx.token.holders
    cfg = ctx.config

    concentrated = h.top10_pct > cfg.max_top10_pct or h.count < cfg.min_holders
    state.scratch["rug_risk"] = c.is_dangerous
    state.scratch["safety_ok"] = not c.is_dangerous and not concentrated

    score = 1.0
    if c.mint_authority_active:
        score -= 0.5
    if c.freeze_authority_active:
        score -= 0.3
    if c.is_honeypot:
        score = 0.0
    if c.bundled_supply:
        score -= 0.4
    if c.dev_rug_history:
        score = 0.0
    score -= max(0.0, h.top10_pct - 0.2) * 0.7  # penalize concentration over 20%
    if c.lp_burned or c.lp_locked:
        score += 0.1
    state.scratch["safety_score"] = _clamp(score)


def intel_gate(state: State) -> None:
    """Wallet-intel + dev-history gate. Hard abort on bundle attack or known rugger.

    Runs AFTER ``safety_gate`` so it only sees tokens that look safe on-chain but
    might still be compromised at the social/launch level.
    """
    ctx = state.context
    w = ctx.token.wallets
    c = ctx.token.contract
    cfg = ctx.config

    too_many_bundlers = w.bundler_wallet_count > cfg.max_bundler_wallets
    low_external = (
        w.safety_score is not None and w.safety_score < cfg.min_gmgn_safety_score
    )
    rug_dev = c.dev_rug_history

    state.scratch["intel_ok"] = not (too_many_bundlers or low_external or rug_dev)
    state.scratch["intel_block_reason"] = (
        "dev rug history" if rug_dev
        else "bundle attack detected" if too_many_bundlers
        else f"external safety score too low ({w.safety_score})" if low_external
        else None
    )


def market_gate(state: State) -> None:
    """Liquidity + volume. Gate against illiquid/dead tokens."""
    ctx = state.context
    m = ctx.token.market
    cfg = ctx.config

    state.scratch["market_ok"] = (
        m.liquidity_usd >= cfg.min_liquidity_usd and m.volume_1h >= cfg.min_volume_1h
    )
    liq = _clamp(m.liquidity_usd / (cfg.min_liquidity_usd * 5))
    vol = _clamp(m.volume_1h / (cfg.min_volume_1h * 5))
    state.scratch["market_score"] = (liq + vol) / 2


def momentum_scorer(state: State) -> None:
    """Short-window buy pressure from ``ActivityData``. Scoring only, no gate.

    Bias toward 0.5 when there are no trades yet (neutral, not zero) so fresh
    launches aren't punished for lack of history.
    """
    a = state.context.token.activity
    total_5m = a.buys_5m + a.sells_5m

    if total_5m == 0:
        state.scratch["momentum_score"] = 0.5
        state.scratch["buy_ratio_5m"] = 0.5
        return

    ratio = a.buy_ratio_5m
    # Volume confidence shrinks the deviation from 0.5 when sample is small.
    vol_conf = _clamp(total_5m / 100)
    centered = 0.5 + (ratio - 0.5) * vol_conf
    state.scratch["buy_ratio_5m"] = round(ratio, 3)
    state.scratch["momentum_score"] = _clamp(centered)


def wallet_intel_scorer(state: State) -> None:
    """Score based on smart-money / KOL presence, penalised by sniper density."""
    w = state.context.token.wallets

    smart = _clamp(w.smart_wallet_buys / 5) * 0.5  # cap at 5 buys = full credit
    kol = _clamp(w.kol_wallet_count / 4) * 0.25
    external = _clamp((w.safety_score or 0) / 100) * 0.25
    sniper_penalty = _clamp(max(0, w.sniper_wallet_count - 5) / 20) * 0.3

    score = smart + kol + external - sniper_penalty
    state.scratch["wallet_score"] = _clamp(score)
    state.scratch["smart_money_strong"] = (
        w.smart_wallet_buys >= state.context.config.smart_money_threshold
    )


def pumpfun_context(state: State) -> None:
    """Compute pumpfun-specific flags. No-op for non-pumpfun tokens."""
    p = state.context.token.pumpfun
    cfg = state.context.config

    if p is None:
        state.scratch["pumpfun_urgency"] = False
        state.scratch["bonding_curve_pct"] = None
        return

    state.scratch["bonding_curve_pct"] = p.bonding_curve_pct
    state.scratch["pumpfun_urgency"] = p.bonding_curve_pct >= cfg.pumpfun_curve_urgency_pct
    state.scratch["pumpfun_mayhem"] = p.is_mayhem_mode


def social_scorer(state: State) -> None:
    """Twitter + telegram alpha + KOL activity. Scoring only, no gate.

    Uses enriched fields (mentions, growth, sentiment, velocity) when available
    while staying backwards compatible with minimal SocialData fixtures.
    """
    s = state.context.token.social
    tw = s.twitter

    # Reach (followers) + raw tweet volume — broad awareness.
    reach = _clamp(tw.followers / 10_000) * 0.25 + _clamp(tw.tweets_1h / 50) * 0.05
    # Mentions + engagement — other people TALKING about it (stronger signal).
    mentions = _clamp(tw.mentions_1h / 300) * 0.15 + _clamp(tw.engagement / 10_000) * 0.10
    # Momentum: velocity + growth rate.
    growth = _clamp(tw.mention_growth_pct / 200) * 0.10
    velocity = _clamp(tw.velocity_tpm / 20) * 0.05
    # Sentiment prior (external service).
    sentiment_bonus = (
        0.10 if tw.sentiment == "bullish"
        else -0.10 if tw.sentiment == "bearish"
        else 0.0
    )
    # Telegram + KOL.
    telegram = (
        _clamp(s.telegram.members / 2_000) * 0.10
        + _clamp(s.telegram.alpha_calls / 5) * 0.05
    )
    kol = _clamp(s.kol_count_5m / 5) * 0.15

    state.scratch["social_score"] = _clamp(
        reach + mentions + growth + velocity + sentiment_bonus + telegram + kol
    )
