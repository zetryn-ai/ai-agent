"""Pure-rule nodes for the KOL copy-trade strategy.

All decisions here are deterministic; no LLM call. They mirror the
sniper's fast-path style (set ``state.output`` and ``goto=__end__`` on
rejection) so the graph can short-circuit without the analyst.

Boundary recap: the framework owns the *rules*; the bot owns the
*data and state*. ``last_copy_ts`` (for cooldown), KOL whitelist
contents, and token enrichment are all bot-supplied via
``KOLContext`` and the injected ``KOLRegistry``.
"""

from __future__ import annotations

from collections.abc import Callable

from trading.schemas import Decision
from zetryn.core import Command, State

from ..kol_registry import KOLRegistry


def _latency_ms(state: State) -> float:
    return round(sum(t.duration_ms for t in state.trace), 4)


def _abort(state: State, reason: str, *, action: str = "skip",
           rug_risk: bool = False) -> Command:
    state.output = Decision(
        action=action,
        confidence=0.0,
        reasons=[reason],
        flags={"rug_risk": rug_risk, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )
    return Command(goto="__end__")


# -- node 1: contract safety -------------------------------------------------


def fast_safety(state: State) -> Command | None:
    """Instant abort on a dangerous contract (reuses TokenInput.contract)."""
    c = state.context.token.contract
    if c.is_dangerous:
        return _abort(
            state,
            "contract unsafe: " + (", ".join(c.notes) or "rug risk"),
            action="abort",
            rug_risk=True,
        )
    return None


# -- node 2: KOL whitelist + signal-quality gate ----------------------------


def make_kol_quality(registry: KOLRegistry) -> Callable[[State], Command | None]:
    """Factory: binds the bot's `KOLRegistry` to a rule node.

    The node enforces, in order:
      1. Wallet is on the whitelist.
      2. Profile clears the pack-wide tier + hit-rate floor.
      3. Profile clears the per-deployment `KOLCopyTradeConfig` floors.
      4. KOL's own buy size meets `profile.min_sol_to_copy`.
      5. Signal is fresh (`event.block_age_seconds` ≤
         `config.max_signal_age_seconds`).
      6. Cooldown respected (`event.detected_at_ts - last_copy_ts` ≥
         `config.kol_cooldown_seconds`).

    Each rejection writes a `Decision(action="skip")` with a precise
    `reasons[]` entry so the bot can log which gate fired.
    """
    _TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}

    def kol_quality(state: State) -> Command | None:
        ctx = state.context
        ev = ctx.event
        cfg = ctx.config

        # 1. on the whitelist at all?
        profile = registry.get(ev.wallet)
        if profile is None:
            return _abort(state, f"unknown KOL wallet: {ev.wallet[:8]}...")

        # 2. pack-wide global floor
        if not registry.passes_global_floor(profile):
            return _abort(
                state,
                f"KOL {profile.name or ev.wallet[:8]} below pack floor "
                f"(tier={profile.tier}, hit_rate={profile.hit_rate:.2f}, "
                f"required tier≥{registry.min_tier} hit_rate≥{registry.min_hit_rate:.2f})",
            )

        # 3. per-deployment floor (tighter than pack)
        my_tier = _TIER_ORDER.get(profile.tier, 99)
        deploy_floor = _TIER_ORDER.get(cfg.min_kol_tier, 99)
        if my_tier > deploy_floor:
            return _abort(
                state,
                f"KOL tier {profile.tier} below deployment min {cfg.min_kol_tier}",
            )
        if profile.hit_rate < cfg.min_kol_hit_rate:
            return _abort(
                state,
                f"KOL hit_rate {profile.hit_rate:.2f} below deployment min "
                f"{cfg.min_kol_hit_rate:.2f}",
            )

        # 4. KOL's own bet must be meaningful
        if ev.sol_amount < profile.min_sol_to_copy:
            return _abort(
                state,
                f"KOL buy size {ev.sol_amount} SOL below profile threshold "
                f"{profile.min_sol_to_copy} SOL",
            )

        # 5. signal staleness
        if ev.block_age_seconds > cfg.max_signal_age_seconds:
            return _abort(
                state,
                f"signal too stale: {ev.block_age_seconds:.1f}s > "
                f"{cfg.max_signal_age_seconds:.0f}s",
            )

        # 6. cooldown
        if ctx.last_copy_ts is not None:
            elapsed = ev.detected_at_ts - ctx.last_copy_ts
            if elapsed < cfg.kol_cooldown_seconds:
                return _abort(
                    state,
                    f"KOL cooldown active: {elapsed:.1f}s since last copy "
                    f"(min {cfg.kol_cooldown_seconds:.0f}s)",
                )

        # All checks passed — record the profile for downstream nodes.
        state.scratch["kol_profile"] = profile
        return None

    kol_quality.__name__ = "kol_quality"
    return kol_quality


# -- node 3: market hard-gate (mirror sniper.fast_market) -------------------


def fast_market(state: State) -> Command | None:
    """Skip if liquidity/volume too thin, or bundler/sniper density too high."""
    m = state.context.token.market
    w = state.context.token.wallets
    cfg = state.context.config

    if m.liquidity_usd < cfg.min_liquidity_usd:
        return _abort(state, f"liquidity ${m.liquidity_usd:,.0f} below min "
                             f"${cfg.min_liquidity_usd:,.0f}")
    if m.volume_1h < cfg.min_volume_1h:
        return _abort(state, f"volume_1h ${m.volume_1h:,.0f} below min "
                             f"${cfg.min_volume_1h:,.0f}")

    h = state.context.token.holders
    if h.top10_pct > cfg.max_top10_pct:
        return _abort(state, f"top10_pct {h.top10_pct:.0%} above max "
                             f"{cfg.max_top10_pct:.0%}")
    if w.bundler_wallet_count > cfg.max_bundler_count:
        return _abort(state, f"bundler_count {w.bundler_wallet_count} above max "
                             f"{cfg.max_bundler_count}")
    if w.sniper_wallet_count > cfg.max_sniper_count:
        return _abort(state, f"sniper_count {w.sniper_wallet_count} above max "
                             f"{cfg.max_sniper_count}")
    return None


# -- node 4: sizing + buy ----------------------------------------------------


def sizing(state: State) -> None:
    """Compute final size and emit the buy Decision (terminal rule node).

    Formula (parameters from KOLCopyTradeConfig):
        kol_conf = clamp((hit_rate - floor) / (ceiling - floor), 0, 1)
        kol_mult = 1 + 2 * kol_conf                       # 1.0 .. 3.0
        top10_pen = 1 - max(0, top10_pct - penalty_start) # 1.0 .. ~0.4
        size = clamp(base_size * kol_mult * top10_pen, 0, max_size)
    """
    cfg = state.context.config
    h = state.context.token.holders
    profile = state.scratch["kol_profile"]   # set by kol_quality

    floor, ceiling = cfg.kol_confidence_floor, cfg.kol_confidence_ceiling
    raw = (profile.hit_rate - floor) / max(ceiling - floor, 1e-9)
    kol_conf = max(0.0, min(1.0, raw))
    kol_mult = 1.0 + 2.0 * kol_conf

    top10_pen = 1.0 - max(0.0, h.top10_pct - cfg.top10_penalty_start)
    top10_pen = max(0.0, min(1.0, top10_pen))

    size = cfg.base_size * kol_mult * top10_pen
    size = max(0.0, min(size, cfg.max_size))

    state.output = Decision(
        action="buy",
        confidence=round(0.5 + 0.5 * kol_conf, 3),  # 0.5..1.0
        size=round(size, 4),
        scores={"kol_confidence": round(kol_conf, 3), "top10_penalty": round(top10_pen, 3)},
        reasons=[
            f"KOL {profile.name or 'unknown'} (tier {profile.tier}, "
            f"hit_rate {profile.hit_rate:.2f})",
            f"size {size:.4f} = base {cfg.base_size} × "
            f"kol_mult {kol_mult:.2f} × top10_pen {top10_pen:.2f}",
        ],
        flags={"rug_risk": False, "llm_failed": False},
        meta={"run_id": state.run_id, "latency_ms": _latency_ms(state)},
    )
