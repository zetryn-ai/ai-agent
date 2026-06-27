"""Trading domain contract (Solana memecoin).

The input is a rich, self-contained ``TokenInput`` the bot fills in (push model):
identity + market + activity + holders + contract safety + wallet intel + pumpfun
(optional) + socials. The output is a ``Decision`` with per-dimension scores.
The framework decides; the bot executes.

A ``DataProvider`` protocol is kept for the pull model (backtest/live fetching):
a provider simply builds a ``TokenInput`` for a mint, so push and pull converge on
the same shape.

All new fields added in the M7 enrichment have safe defaults so older callers and
fixtures continue to work without changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

# -- input signal groups (supplied by the bot) -------------------------------


class MarketData(BaseModel):
    mcap: float = 0.0
    liquidity_usd: float = 0.0
    volume_1h: float = 0.0
    volume_24h: float = 0.0
    price: float | None = None
    # ``age_minutes`` is kept for backwards compat; prefer ``age_seconds`` for
    # sub-minute precision on fresh pumpfun launches.
    age_minutes: float | None = None
    age_seconds: float | None = None
    txns_1h: int = 0


class ActivityData(BaseModel):
    """Short-window trading activity (volume / txns / buy-sell breakdown).

    Separated from ``MarketData`` because these change every few seconds while
    market-level facts (mcap, liquidity) change slower. Keeping them apart makes
    snapshots/diffs cheaper and prompts cleaner.
    """

    volume_1m_usd: float = 0.0
    volume_5m_usd: float = 0.0
    volume_1h_usd: float = 0.0
    txns_1m: int = 0
    txns_5m: int = 0
    buys_5m: int = 0
    sells_5m: int = 0

    @property
    def buy_ratio_5m(self) -> float:
        """Buy pressure 0..1. Returns 0.5 (neutral) when no trades observed."""
        total = self.buys_5m + self.sells_5m
        return self.buys_5m / total if total > 0 else 0.5


class HolderData(BaseModel):
    count: int = 0
    top10_pct: float = 1.0  # 0..1 concentration in top 10 holders
    dev_pct: float = 0.0


class ContractData(BaseModel):
    mint_authority_active: bool = False
    freeze_authority_active: bool = False
    lp_burned: bool = False
    lp_locked: bool = False
    is_honeypot: bool = False
    # Supply controlled by a coordinated bundle of wallets at launch.
    bundled_supply: bool = False
    # Creator wallet has rugged previous tokens (off-chain signal from intel feed).
    dev_rug_history: bool = False
    notes: list[str] = Field(default_factory=list)

    @property
    def is_dangerous(self) -> bool:
        return (
            self.mint_authority_active
            or self.freeze_authority_active
            or self.is_honeypot
            or self.bundled_supply
            or self.dev_rug_history
        )


class WalletIntel(BaseModel):
    """Per-token wallet classification (GMGN-style).

    Counts are what the agent decides on. Address lists are optional and exist
    for cross-token memory features (blacklist, reputation) added later — they
    are NOT fed into LLM prompts to keep them cheap.
    """

    # External safety score 0..100 (RugCheck / GMGN). None means "not available".
    safety_score: float | None = None
    smart_wallet_buys: int = 0  # how many proven-profitable wallets bought
    smart_wallet_count: int = 0  # how many such wallets currently hold
    kol_wallet_count: int = 0
    sniper_wallet_count: int = 0  # bots that bought at launch
    bundler_wallet_count: int = 0  # coordinated launch manipulation
    whale_wallet_count: int = 0
    # Optional address lists (tier-2 memory; off by default to keep prompts cheap).
    smart_wallets: list[str] = Field(default_factory=list)
    kol_wallets: list[str] = Field(default_factory=list)
    sniper_wallets: list[str] = Field(default_factory=list)
    bundler_wallets: list[str] = Field(default_factory=list)
    whale_wallets: list[str] = Field(default_factory=list)


class PumpfunData(BaseModel):
    """Pump.fun bonding curve state. Only relevant when ``source == 'pumpfun_ws'``."""

    creator_wallet: str | None = None
    creator_sol_buy: float = 0.0  # SOL the creator invested at launch
    bonding_curve_pct: float = 0.0  # 0..100 graduation progress
    is_mayhem_mode: bool = False  # pumpfun turbo regime flag


class TwitterData(BaseModel):
    handle: str | None = None
    followers: int = 0
    tweets_1h: int = 0
    # Enriched mention/sentiment signals (from external sentiment service).
    mentions_1h: int = 0  # how many people are TALKING about it
    mention_growth_pct: float = 0.0  # vs previous hour, -100..+inf
    sentiment: Literal["bullish", "neutral", "bearish"] | None = None
    engagement: int = 0  # likes + RT + replies (quality, not noise)
    velocity_tpm: float = 0.0  # tweets per minute over last 30m


class TelegramData(BaseModel):
    members: int = 0
    alpha_calls: int = 0  # mentions in alpha channels recently


class SocialData(BaseModel):
    twitter: TwitterData = Field(default_factory=TwitterData)
    telegram: TelegramData = Field(default_factory=TelegramData)
    kol_wallets: list[str] = Field(default_factory=list)
    kol_count_5m: int = 0  # distinct KOL wallets buying in last 5 min
    website: str | None = None
    # Paid DexScreener boost. Stored but not currently scored — interpretation is
    # ambiguous (real attention vs paid trap) until outcome data calibrates it.
    boost_amount: float = 0.0
    boost_total_amount: float = 0.0


# Where a token observation came from. Affects how the framework interprets data
# (a pumpfun token at 30s of age behaves very differently from a DexScreener
# token of the same age).
TokenSource = Literal["pumpfun_ws", "dexscreener", "raydium", "birdeye", "manual"]


class TokenInput(BaseModel):
    """Everything the bot knows about one token, pushed in for a decision."""

    mint: str
    symbol: str = ""
    name: str = ""
    source: TokenSource = "manual"
    market: MarketData = Field(default_factory=MarketData)
    activity: ActivityData = Field(default_factory=ActivityData)
    holders: HolderData = Field(default_factory=HolderData)
    contract: ContractData = Field(default_factory=ContractData)
    wallets: WalletIntel = Field(default_factory=WalletIntel)
    pumpfun: PumpfunData | None = None
    social: SocialData = Field(default_factory=SocialData)


@runtime_checkable
class DataProvider(Protocol):
    """Pull model: build a TokenInput for a mint (backtest/live)."""

    async def fetch(self, mint: str) -> TokenInput: ...


# -- LLM advisor output ------------------------------------------------------


class NarrativeScore(BaseModel):
    """Legacy single-aspect score, kept for backwards compat with M0..M7 strategies."""

    score: float = Field(ge=0, le=1, description="0..1 quality of narrative/hype")
    sentiment: Literal["bullish", "neutral", "bearish"]
    rug_signals: list[str] = Field(default_factory=list)
    reasoning: str = ""


class AspectAnalysis(BaseModel):
    """One dimension of the analyst's verdict (safety, market, wallets, social)."""

    score: float = Field(ge=0, le=1)
    verdict: Literal["positive", "neutral", "negative"]
    signals: list[str] = Field(default_factory=list)
    reasoning: str = ""


class AuditVerdict(BaseModel):
    """LLM second-opinion on a rule-decided snipe entry (M9 hybrid_audit).

    Produced asynchronously AFTER the sniper has already returned its rule-based
    decision. Written to ``DecisionLog`` (by the bot) for offline analysis — where
    do rule and AI agree / disagree, and what does that mean for future tuning.
    Never blocks the trading hot path.
    """

    agrees: bool
    confidence: float = Field(ge=0, le=1)
    concerns: list[str] = Field(default_factory=list)
    reasoning: str = ""


class FullAnalysis(BaseModel):
    """Structured multi-aspect verdict from the AI analyst (M8 scanner output).

    One rich LLM call returns this whole structure: per-aspect score + verdict +
    reasoning, plus a final synthesised recommendation. The framework's guardrail
    rule may downgrade the recommendation but never upgrades it.
    """

    safety: AspectAnalysis
    market: AspectAnalysis
    wallets: AspectAnalysis
    social: AspectAnalysis
    final_score: float = Field(ge=0, le=1)
    recommendation: Literal["alert", "watch", "skip"]
    reasoning: str = ""


# -- configuration -----------------------------------------------------------


class ScannerConfig(BaseModel):
    min_liquidity_usd: float = 5_000
    min_volume_1h: float = 10_000
    max_top10_pct: float = 0.5
    min_holders: int = 50
    # New thresholds for enriched signals (all optional gates).
    max_bundler_wallets: int = 3  # >this triggers bundle_check abort
    max_sniper_wallets: int = 15  # >this lowers confidence (bot war)
    min_gmgn_safety_score: float = 40.0  # external score floor (0..100)
    smart_money_threshold: int = 3  # >=this buys = strong signal
    min_buy_ratio_5m: float = 0.45  # below this = sell pressure
    pumpfun_curve_urgency_pct: float = 85.0  # near-graduation alert mode
    use_llm: bool = True
    alert_threshold: float = 0.7
    watch_threshold: float = 0.4
    # Weights for the final score across dimensions (renormalized over those used).
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "safety": 0.25,
            "market": 0.25,
            "social": 0.15,
            "narrative": 0.15,
            "wallets": 0.10,
            "momentum": 0.10,
        }
    )


class SniperConfig(BaseModel):
    """Fast-path config for the auto-snipe agent.

    The sniper prioritizes speed: by default it runs pure-rule (sub-second, no LLM).
    Enable ``use_llm`` only if you accept the latency for an LLM-decided/hybrid entry.
    """

    min_liquidity_usd: float = 3_000
    min_volume_1h: float = 5_000
    max_top10_pct: float = 0.6
    min_holders: int = 30
    base_size: float = 1.0  # nominal position size (units defined by the bot)
    max_size: float = 5.0  # hard cap the LLM/sizing can never exceed
    use_llm: bool = False  # decide/hybrid mode; off = pure-rule fast path
    decision_mode: str = "rule"  # "rule" | "llm" | "hybrid"


# -- context (input wrapper) and output --------------------------------------


@dataclass
class TradingContext:
    """What the bot hands the framework for one decision."""

    token: TokenInput
    config: ScannerConfig = field(default_factory=ScannerConfig)
    positions: dict[str, Any] = field(default_factory=dict)


class Decision(BaseModel):
    """The framework's output. The bot executes (or not) based on this."""

    action: Literal[
        "alert", "watch", "skip", "buy", "abort",
        # Position-management actions (v0.13.0 / PL1)
        "hold", "take_profit", "scale_out", "exit_full",
    ]
    confidence: float = Field(ge=0, le=1, default=0.0)
    size: float | None = None
    scores: dict[str, float] = Field(default_factory=dict)  # safety/market/social/...
    reasons: list[str] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)  # rug_risk, llm_failed, classification
    meta: dict[str, Any] = Field(default_factory=dict)  # run_id, latency_ms
    # Full analyst verdict (M8+). Populated by AI-first scanners; None for
    # hard-gate rejects and legacy/rule-only paths.
    analysis: FullAnalysis | None = None


# -- KOL copy-trade strategy (v0.6.0) ----------------------------------------
#
# Schemas only. The framework defines the shape; the bot fetches and fills
# every field. See docs/plans/2026-06-25-kol-copytrade-strategy.md §0.5
# for the boundary contract.


class KOLAnalystVerdict(BaseModel):
    """LLM analyst's verdict in the KOL copy-trade `confirmed` mode.

    The analyst sees a token that already passed all hard rules + the
    KOL whitelist check. Its job is NOT to decide "should we buy" (the
    rules implied yes) — it's to detect qualitative red flags the rules
    cannot see, and to nudge size up or down based on how much
    confluence it observes across the fact sheet.
    """

    approve: bool = Field(
        description="True = proceed with the rule-sized buy. False = skip "
        "(rules would have bought; the analyst is vetoing on qualitative "
        "concerns the rule layer cannot encode)."
    )
    size_multiplier: float = Field(
        ge=0.0, le=1.5,
        description="Multiplier applied to the rule-derived size. 1.0 = full "
        "rule size. 0.5 = half (less confident). 1.5 = ceiling boost (strong "
        "confluence). Ignored when approve=False.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How confident the analyst is in the verdict (independent "
        "of approve direction).",
    )
    concerns: list[str] = Field(
        default_factory=list,
        description="Short phrases naming qualitative red flags. Empty list "
        "means no concerns. Surfaced into Decision.reasons for auditability.",
    )
    reasoning: str = Field(
        default="",
        description="One- or two-sentence synthesis of why the analyst "
        "approved / vetoed / adjusted size.",
    )


class KOLProfile(BaseModel):
    """One KOL's historical performance, as the bot computes it offline.

    Stored inside the bot's `KnowledgePack` under
    `data/kol_whitelist.json -> wallets[<address>]`. The framework reads
    these values to score / reject incoming copy-trade signals.
    """

    name: str = ""                              # human-friendly label
    hit_rate: float = Field(ge=0, le=1, default=0.0)
    avg_pnl_pct: float = 0.0
    trades_30d: int = 0
    exit_pattern: str = ""                      # e.g. "scales_out_50pct"
    tier: Literal["S", "A", "B", "C"] = "C"
    min_sol_to_copy: float = 0.0                # ignore KOL buys below this size


class KOLBuyEvent(BaseModel):
    """A KOL wallet just bought a token.

    Built by the BOT from its event stream (Helius webhook, Cielo
    subscription, custom indexer). The framework never produces one.
    """

    wallet: str
    mint: str
    sol_amount: float = Field(ge=0)
    detected_at_ts: float                       # unix ts (bot's clock)
    block_age_seconds: float = Field(ge=0)      # how stale this signal is


class KOLCopyTradeConfig(BaseModel):
    """Tunables for the copy-trade strategy.

    Per-deployment overridable; the formula in the `sizing` node reads
    these without touching code. Defaults are placeholders — tune from
    real outcome data.
    """

    # safety / liquidity gates (mirror SniperConfig defaults)
    min_liquidity_usd: float = 3_000
    min_volume_1h: float = 5_000
    max_top10_pct: float = 0.6
    max_bundler_count: int = 3
    max_sniper_count: int = 10

    # KOL whitelist gates
    min_kol_tier: Literal["S", "A", "B", "C"] = "A"
    min_kol_hit_rate: float = Field(ge=0, le=1, default=0.40)
    max_signal_age_seconds: float = 30.0        # reject if signal is too stale
    kol_cooldown_seconds: float = 60.0          # min gap between copies of same KOL

    # sizing formula tunables (sizing = base × (1 + 2·kol_conf) × token_safety)
    base_size: float = 1.0
    max_size: float = 5.0
    kol_confidence_floor: float = 0.40          # hit_rate below this → conf=0
    kol_confidence_ceiling: float = 0.70        # hit_rate at/above this → conf=0.30
    top10_penalty_start: float = 0.20           # penalise size when top10 > this

    decision_mode: Literal["rule", "confirmed", "audit"] = "rule"


@dataclass
class KOLContext:
    """What the bot hands `build_kol_copytrade(...)` for one decision."""

    event: KOLBuyEvent
    token: TokenInput
    config: KOLCopyTradeConfig = field(default_factory=KOLCopyTradeConfig)
    # When this KOL was last copied (bot-tracked; None = no recent copy).
    # Used by `kol_quality` to enforce `config.kol_cooldown_seconds`.
    last_copy_ts: float | None = None
    positions: dict[str, Any] = field(default_factory=dict)


# -- Graduation snipe strategy (v0.12.0) -------------------------------------
#
# Schemas only. The bot subscribes to Pump.fun WS events, fills the
# `GraduationEvent` from bonding-curve + Raydium pair data, enriches the
# `TokenInput`, and hands the framework a `GraduationContext`. The framework
# returns a `Decision`; the bot executes.


class GraduationEvent(BaseModel):
    """Per-graduation snapshot the bot pushes to the framework.

    Captures bonding-curve fill dynamics and the Raydium pair structure at
    the moment a Pump.fun token graduates. The bot owns the WS subscription
    and enrichment; the framework only reads.
    """

    mint: str
    pair_address: str
    detected_at_ts: float

    pair_age_seconds: float

    # Bonding curve signals
    bonding_curve_fill_seconds: float
    bonding_curve_unique_buyers: int
    bonding_curve_sol_raised: float
    bonding_curve_premium_pct: float

    # Raydium pair signals
    initial_liquidity_sol: float
    initial_liquidity_token_pct: float
    lp_burned: bool


class GraduationConfig(BaseModel):
    """Tunables for the Pump.fun graduation snipe strategy."""

    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"

    # Graduation-specific gate thresholds
    max_fill_seconds: float = 300.0
    min_unique_buyers: int = 50
    min_initial_liquidity_sol: float = 30.0
    require_lp_burned: bool = True
    max_pair_age_seconds: float = 10.0
    max_premium_pct: float = 20.0

    # Token-quality gates (mirrors SniperConfig style)
    min_liquidity_usd: float = 3_000
    min_volume_1h: float = 0.0
    max_top10_pct: float = 0.6
    max_bundler_wallets: int = 3
    max_sniper_wallets: int = 15

    # Sizing
    base_size: float = 0.5
    max_size: float = 2.0


@dataclass
class GraduationContext:
    """What the bot hands `build_graduation(...)` for one event."""

    token: TokenInput
    event: GraduationEvent
    config: GraduationConfig = field(default_factory=GraduationConfig)


class GraduationVerdict(BaseModel):
    """Structured LLM output for the graduation snipe decider."""

    action: Literal["buy", "skip", "abort"]
    confidence: float = Field(ge=0, le=1)
    size_pct: float = Field(ge=0, le=1)
    reasoning: str = ""
    concerns: list[str] = Field(default_factory=list)


# -- Position Lifecycle Helpers (v0.13.0 / PL1) ------------------------------
#
# First position-management agent. Framework decides hold / TP / scale_out /
# exit_full on an open position. The bot owns position persistence; it
# pushes a fresh `PositionContext` per tick.


class PartialExit(BaseModel):
    """A ladder rung already executed by the bot. Used to skip rungs that
    have already been hit so the agent doesn't recommend selling twice."""

    sold_at_pnl_pct: float
    sold_size: float
    sold_at_ts: float


class PositionState(BaseModel):
    """Complete snapshot of an open position, pushed by the bot per tick."""

    entry_price: float
    entry_size: float
    entry_ts: float

    current_price: float
    current_size: float       # what's left after any partial exits
    pnl_pct: float            # (current - entry) / entry — signed
    holding_seconds: float

    peak_pnl_pct: float = 0.0
    drawdown_from_peak_pct: float = 0.0

    partial_exits: list[PartialExit] = Field(default_factory=list)


class LifecycleConfig(BaseModel):
    """Tunables for position-management decisions."""

    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"

    # Hard exits (always evaluated, even in llm/hybrid)
    stop_loss_pct: float = -0.30
    max_hold_seconds: float = 3600.0
    trailing_drawdown_pct: float = 0.50
    trailing_arms_at_pnl_pct: float = 0.20

    # TP ladder: list of (pnl_threshold, fraction_of_current_size_to_sell)
    # Default: at +50% sell half (recoup initials), at +100% sell half of
    # remainder, at +300% sell everything.
    tp_ladder: list[tuple[float, float]] = Field(
        default_factory=lambda: [(0.5, 0.5), (1.0, 0.5), (3.0, 1.0)]
    )

    # Safety
    min_sell_size: float = 0.0


@dataclass
class PositionContext:
    """What the bot hands `build_lifecycle(...)` per tick."""

    token: TokenInput
    position: PositionState
    config: LifecycleConfig = field(default_factory=LifecycleConfig)


class LifecycleVerdict(BaseModel):
    """Structured LLM output for lifecycle decider.

    Note: ``stop_loss`` is intentionally NOT in the action set — that's a
    deterministic-only action fired by the rule gate. The LLM operates
    inside the envelope where hard exits have already been checked.
    """

    action: Literal["hold", "take_profit", "scale_out", "exit_full"]
    size_pct: float = Field(ge=0, le=1, description="fraction of CURRENT position to sell")
    confidence: float = Field(ge=0, le=1)
    reasoning: str = ""
    concerns: list[str] = Field(default_factory=list)


# -- Smart Money Confluence (v0.14.0 / S5) -----------------------------------
#
# Fires when ≥ N pre-vetted smart wallets have accumulated the same token
# within a rolling window. The bot subscribes to wallet feeds (Cielo, GMGN,
# Helius), aggregates per-mint accumulations, fills a `ConfluenceEvent`, and
# hands the framework a `ConfluenceContext`. The framework returns a
# `Decision`; the bot executes.


class SmartWalletProfile(BaseModel):
    """Historical performance of one smart wallet, bot-computed offline.

    Stored inside the bot's `KnowledgePack` under
    `data/smart_wallet_whitelist.json -> wallets[<address>]`. Unlike
    `KOLProfile`, smart wallets are anonymous — no name or exit_pattern;
    edge comes from on-chain track record only.
    """

    hit_rate: float = Field(ge=0, le=1, default=0.0)
    avg_pnl_pct: float = 0.0
    trades_30d: int = 0
    tier: Literal["S", "A", "B", "C"] = "C"
    min_sol_to_copy: float = 0.0


class SmartWalletAccumulation(BaseModel):
    """One smart wallet's buy event within the rolling window.

    Built by the BOT from its wallet feed (Cielo, GMGN, Helius, custom
    indexer). The framework never produces one.
    """

    wallet: str
    mint: str
    sol_amount: float = Field(ge=0)
    detected_at_ts: float
    block_age_seconds: float = Field(ge=0)


class ConfluenceEvent(BaseModel):
    """Aggregated confluence snapshot the bot pushes per detected signal.

    The bot fills `accumulations` with every qualifying buy in the window.
    Framework nodes derive stats (unique wallet count, total SOL, avg
    quality) from the list — no pre-aggregation required.
    """

    mint: str
    detected_at_ts: float
    window_seconds: float
    accumulations: list[SmartWalletAccumulation] = Field(default_factory=list)


class ConfluenceConfig(BaseModel):
    """Tunables for the Smart Money Confluence strategy."""

    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"

    # Confluence gate
    min_wallet_count: int = Field(ge=1, default=5)
    min_sol_per_wallet: float = 0.5
    max_signal_age_seconds: float = 60.0
    min_hit_rate: float = Field(ge=0, le=1, default=0.35)
    min_tier: Literal["S", "A", "B", "C"] = "B"

    # Market gates (mirror SniperConfig style)
    min_liquidity_usd: float = 3_000
    min_volume_1h: float = 0.0
    max_top10_pct: float = 0.6
    max_bundler_wallets: int = 3
    max_sniper_wallets: int = 15

    # Sizing
    base_size: float = 1.0
    max_size: float = 5.0


@dataclass
class ConfluenceContext:
    """What the bot hands `build_confluence(...)` for one signal."""

    token: TokenInput
    event: ConfluenceEvent
    config: ConfluenceConfig = field(default_factory=ConfluenceConfig)


class ConfluenceVerdict(BaseModel):
    """Structured LLM output for the confluence decider."""

    action: Literal["buy", "skip", "abort"]
    confidence: float = Field(ge=0, le=1)
    size_pct: float = Field(ge=0, le=1)
    reasoning: str = ""
    concerns: list[str] = Field(default_factory=list)


# -- Early-Stage Dip Buy (v0.15.0 / S6) -------------------------------------
#
# One agent, two events. After launch or graduation a dump wave follows;
# S6 waits for it to settle and enters when sell pressure thins out,
# holders retain, and unique buyers recover. The bot monitors the time-
# series and pushes a `DipBuyContext` per candidate settlement window.
# The framework validates timing + dip depth + recovery signals and
# returns a `Decision`.


class DipBuySnapshot(BaseModel):
    """Post-event market snapshot the bot pushes to the framework.

    The bot owns the time-series (candles, trades, holder history) and
    distills it into this flat snapshot. The framework never fetches or
    aggregates — it only reads and validates.
    """

    event_type: Literal["launch", "graduation"]
    mint: str
    detected_at_ts: float
    time_since_event_seconds: float = Field(ge=0)

    # Dip metrics
    price_vs_ath_pct: float = Field(
        description="(current_price / post_event_ath) - 1. Negative means dipped below ATH.",
    )
    sell_pressure_score: float = Field(
        ge=0, le=1,
        description="Bot-computed: 0=no selling, 1=extreme selling.",
    )

    # Recovery signals
    buy_ratio_5m: float = Field(ge=0, le=1, default=0.5)
    holder_retention_pct: float = Field(
        ge=0, le=1, default=0.0,
        description="Fraction of holders that stayed through the dump.",
    )
    unique_buyers_trend: float = Field(
        ge=-1, le=1, default=0.0,
        description="Positive=unique buyers rising, negative=falling.",
    )
    price_stable_seconds: float = Field(
        ge=0, default=0.0,
        description="How long price has not made a new low.",
    )


class DipBuyConfig(BaseModel):
    """Tunables for the Early-Stage Dip Buy strategy."""

    event_type: Literal["launch", "graduation"] = "launch"
    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"

    # Timing window (seconds since the triggering event)
    min_time_since_event_seconds: float = 60.0
    max_time_since_event_seconds: float = 600.0   # ~10 min for launch; set 1800 for grad

    # Dip gate
    min_dip_pct: float = Field(
        ge=0, default=0.15,
        description="Minimum drop from post-event ATH required (e.g. 0.15 = must be ≥15% below ATH).",
    )
    max_sell_pressure_score: float = Field(ge=0, le=1, default=0.35)

    # Recovery gates
    min_buy_ratio_5m: float = Field(ge=0, le=1, default=0.52)
    min_holder_retention_pct: float = Field(ge=0, le=1, default=0.65)
    min_unique_buyers_trend: float = Field(ge=-1, le=1, default=0.0)
    min_price_stable_seconds: float = Field(ge=0, default=30.0)

    # Market gates
    min_liquidity_usd: float = 3_000
    max_top10_pct: float = 0.65
    max_bundler_wallets: int = 3
    max_sniper_wallets: int = 15

    # Sizing
    base_size: float = 0.75
    max_size: float = 3.0


@dataclass
class DipBuyContext:
    """What the bot hands `build_dip_buy(...)` for one candidate entry."""

    token: TokenInput
    snapshot: DipBuySnapshot
    config: DipBuyConfig = field(default_factory=DipBuyConfig)


class DipBuyVerdict(BaseModel):
    """Structured LLM output for the dip-buy decider."""

    action: Literal["buy", "skip", "abort"]
    confidence: float = Field(ge=0, le=1)
    size_pct: float = Field(ge=0, le=1)
    reasoning: str = ""
    concerns: list[str] = Field(default_factory=list)


# -- Organic Growth Detector (v0.16.0 / A1) ----------------------------------
#
# Triage filter — classifies a token's post-launch time-series as organic,
# suspicious, or manipulated based on chart-pattern features. The bot
# watches candle/trade data, computes aggregate signals, and pushes a
# GrowthContext. The framework scores the signals and returns a Decision
# with action ∈ {buy=promote, skip=neutral, abort=manipulated}.


class GrowthSnapshot(BaseModel):
    """Aggregate time-series features the bot computes from candle/trade data.

    The bot owns the time-series (candles, per-minute unique buyers,
    holder history) and distils it into this flat snapshot. The framework
    never fetches or aggregates — it only reads and scores.
    """

    mint: str
    detected_at_ts: float
    observation_seconds: float = Field(ge=0)
    candle_count: int = Field(ge=0)

    # Price pattern — bot classifies from its candle sequence
    price_trajectory: Literal[
        "steady_climb", "vertical_pump", "volatile", "flat", "declining"
    ]

    # Sell presence — key manipulation tell
    sell_presence_pct: float = Field(
        ge=0, le=1,
        description="Fraction of candles with meaningful sell volume. "
        "Near-zero = zero-sell coordinated pump.",
    )

    # Buyer dynamics
    unique_buyer_trend: float = Field(
        ge=-1, le=1, default=0.0,
        description="Positive = new unique buyers joining over the window.",
    )
    holder_growth_rate: float = Field(
        ge=0, default=0.0,
        description="New holders per minute over the observation window.",
    )

    # Pullback pattern
    has_healthy_pullback: bool = False
    max_drawdown_pct: float = Field(
        ge=0, le=1, default=0.0,
        description="Worst intra-window pullback. Organic = 0.05–0.25.",
    )

    # Volume pattern
    whale_volume_pct: float = Field(
        ge=0, le=1, default=0.0,
        description="Fraction of volume from whale wallets.",
    )
    volume_acceleration: float = Field(
        ge=0, default=1.0,
        description="recent_volume / early_volume. > 1.5 = accelerating demand.",
    )


class GrowthConfig(BaseModel):
    """Tunables for the Organic Growth Detector."""

    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"

    # Observation gate
    min_observation_seconds: float = 120.0
    min_candle_count: int = 5

    # Scoring thresholds
    min_sell_presence_pct: float = Field(ge=0, le=1, default=0.03)
    max_sell_presence_pct: float = Field(ge=0, le=1, default=0.70)
    min_unique_buyer_trend: float = Field(ge=-1, le=1, default=-0.20)
    max_whale_volume_pct: float = Field(ge=0, le=1, default=0.65)

    # Classification thresholds (organic_score out of 1.0)
    organic_score_threshold: float = Field(ge=0, le=1, default=0.65)
    suspicious_score_threshold: float = Field(ge=0, le=1, default=0.35)


@dataclass
class GrowthContext:
    """What the bot hands `build_organic_detector(...)` for one token."""

    token: TokenInput
    snapshot: GrowthSnapshot
    config: GrowthConfig = field(default_factory=GrowthConfig)


class GrowthVerdict(BaseModel):
    """Structured LLM output for the organic growth classifier.

    `classification` maps to `Decision.action`:
      organic     → buy   (promote scanner candidate)
      suspicious  → skip  (neutral — normal scanner flow)
      manipulated → abort (demote — skip scanner, add to cooldown)
    """

    classification: Literal["organic", "suspicious", "manipulated"]
    confidence: float = Field(ge=0, le=1)
    promote_scanner: bool = True
    signals: list[str] = Field(default_factory=list)
    reasoning: str = ""
