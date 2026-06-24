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

    action: Literal["alert", "watch", "skip", "buy", "abort"]
    confidence: float = Field(ge=0, le=1, default=0.0)
    size: float | None = None
    scores: dict[str, float] = Field(default_factory=dict)  # safety/market/social/...
    reasons: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)  # rug_risk, llm_failed
    meta: dict[str, Any] = Field(default_factory=dict)  # run_id, latency_ms
    # Full analyst verdict (M8+). Populated by AI-first scanners; None for
    # hard-gate rejects and legacy/rule-only paths.
    analysis: FullAnalysis | None = None
