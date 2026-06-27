# Strategy Catalog

Single source of truth for every reference strategy in this repo — what
ships today, what's planned, and what's been considered but rejected.

For roadmap status (versions shipped, milestones) see
[CAPABILITIES.md §6](CAPABILITIES.md#6-roadmap). For per-strategy design
specs see [plans/](plans/). For non-roadmap changes (refactors, fixes)
see [maintenance-log.md](maintenance-log.md).

**Tier definitions (used below):**

| Tier | Meaning |
|---|---|
| **S** | Edge-defining. Distinct signal not already captured by another agent. Build next. |
| **A** | Strong fit, complementary. Build after current S-tier ships. |
| **B** | Plausible but incremental — partial overlap with an existing agent. |
| **C** | Considered, not pursued. Reason recorded. |

---

## Shipped strategies

### Scanner (v0.1.0, hardened v0.3.0)
- **Agent:** `build_scanner(llm)` → `strategies/agents/scanner.py`
- **Input:** `TradingContext(token, config: ScannerConfig)`
- **Modes:** AI-first single LLM call with hard gates + guardrail
- **Use case:** Triage a stream of candidate tokens; emit `alert` / `watch` / `skip`
- **Distinct signal:** Multi-aspect narrative + structure analysis (safety, market, wallets, social)

### Sniper (v0.1.0, +reflect v0.11.0)
- **Agent:** `build_sniper(llm_client?, decision_log?)` → `strategies/agents/sniper.py`
- **Input:** `TradingContext(token, config: SniperConfig)`
- **Modes:** `rule` / `llm` / `hybrid` / `hybrid_audit`
- **Use case:** Speed-first entry on already-filtered tokens
- **Distinct signal:** Sub-ms rule path; optional LLM with deterministic guardrail

### KOL Copy-Trade (v0.6.0 → v0.11.0, K1–K7)
- **Agent:** `build_kol_copytrade(pack|registry, mode, ...)` → `strategies/agents/kol_copytrade.py`
- **Input:** `KOLContext(event: KOLBuyEvent, token, config)`
- **Modes:** `rule` / `confirmed` / `audit`
- **Use case:** Copy a vetted KOL wallet's buy with sizing scaled by their hit-rate
- **Distinct signal:** Per-wallet historical performance (`KOLProfile`) + cooldown

### Pump.fun Graduation Snipe (v0.12.0)
- **Agent:** `build_graduation(llm_client?, decision_log?)` → `strategies/agents/graduation.py`
- **Input:** `GraduationContext(token, event: GraduationEvent, config)`
- **Modes:** `rule` / `llm` / `hybrid` / `hybrid_audit`
- **Use case:** Snipe a Pump.fun token in the 5–30s window after Raydium graduation
- **Distinct signal:** Bonding-curve demand quality (fill speed, unique buyers, premium)

---

## Roadmap strategies — S-tier (build next)

### Position Lifecycle Helpers
**ID:** PL1 · **Tier:** S · **Status:** planned · **Spec:** TBD (`docs/plans/YYYY-MM-DD-position-lifecycle.md`)

**Why S-tier:** Every existing agent (scanner / sniper / KOL / graduation) decides *entry*. Nothing in the framework helps with *exit*. The bot is on its own once filled — meaning users have to bolt on their own TP/SL logic outside the framework. This is the biggest single gap.

**Boundary check (NON-NEGOTIABLE):** Framework returns *recommendations*. Bot owns the open position, live price stream, MEV, slippage, signing. No position persistence inside the framework — bot pushes `PositionContext` per tick.

**Proposed shape:**

```python
class PositionState(BaseModel):
    entry_price: float
    entry_size: float
    current_price: float
    pnl_pct: float
    holding_seconds: float
    peak_pnl_pct: float          # high-water mark since entry
    drawdown_from_peak_pct: float

class LifecycleConfig(BaseModel):
    take_profit_pcts: list[float] = [0.5, 1.0, 3.0]   # scale-out ladder
    stop_loss_pct: float = -0.3
    trailing_drawdown_pct: float = 0.5                 # exit on 50% give-back
    max_hold_seconds: float = 3600
    decision_mode: Literal["rule", "llm", "hybrid"] = "rule"

@dataclass
class PositionContext:
    token: TokenInput
    position: PositionState
    config: LifecycleConfig = field(default_factory=LifecycleConfig)
```

Output `Decision.action ∈ {hold, take_profit, stop_loss, scale_out, exit_full}` with `size` = how much to sell (for scale_out / take_profit).

**Why distinct from entry agents:** Different state shape (open position), different decision space (sell-side ladder, not buy/skip/abort), different feature set (PnL trajectory, time-in-trade, drawdown-from-peak).

### Strategy #5 — Smart Money Confluence
**ID:** S5 · **Tier:** S · **Status:** planned · **Spec:** TBD

**Why S-tier:** Smart-wallet activity is currently a *scoring input* inside scanner/sniper, not a primary trigger. A dedicated agent fires only when **multiple** vetted smart wallets converge on the same token within a window — a much higher-precision signal than "1 smart wallet bought" buried in a scanner score.

**Proposed shape:**

```python
class SmartWalletBuy(BaseModel):
    wallet: str
    sol_amount: float
    detected_at_ts: float

class SmartConfluenceEvent(BaseModel):
    mint: str
    buys: list[SmartWalletBuy]                # all qualifying buys in the window
    window_seconds: float
    first_buy_ts: float
    distinct_smart_wallets: int

class SmartConfluenceConfig(BaseModel):
    min_distinct_wallets: int = 3
    max_window_seconds: float = 120.0
    min_wallet_hit_rate: float = 0.5          # per-wallet floor (lookup in registry)
    require_no_bundler_overlap: bool = True
    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"
```

Reuses sniper's `fast_safety` + a generalized `market_gate`. New registry: `SmartWalletRegistry` (parallel to `KOLRegistry`, sourced from `KnowledgePack`).

**Why distinct from KOL Copy-Trade:** KOL is *single-wallet* (one trusted signal → copy). Confluence is *multi-wallet correlation* (cluster of independent smart wallets converging = much stronger).

---

## Roadmap strategies — A-tier

### Strategy #6 — Migration Front-Run
**Tier:** A · **Status:** considered

Detect tokens migrating between DEXes (e.g. Raydium → Meteora, Orca → Raydium pool upgrade) and front-run the new pair. Distinct from graduation snipe because the token is *not* a new launch — it has price history, holders, established narrative. Different feature set (migration urgency, liquidity ratio shift, holder retention post-migration).

**Build after:** PL1 + S5 ship.

### Strategy #7 — Re-Accumulation Detector
**Tier:** A · **Status:** considered

Token already had its first leg, dumped 60–80%, and is showing accumulation: low-volume buying from smart wallets, tightening sell pressure, holder count rising again. Different temporal shape from any current agent (post-dump, not new launch).

**Build after:** PL1 ships (re-entries especially benefit from lifecycle helpers).

---

## Considered, NOT pursued (B/C-tier)

### Volume Spike Scanner — **B-tier**
Reason: too easy to bait. A whale wash-trading their own bag triggers the same signal as organic momentum. Existing scanner already weights volume; a dedicated agent doesn't add a *distinct* signal.

### Twitter Sentiment Pump — **C-tier**
Reason: leading indicator quality is too low. By the time sentiment data lags into the framework, the move is already 10x done. Twitter signals belong as *scoring input* (already in `SocialData`), not as a primary trigger.

### Whale Wallet Mirror (single whale, not confluence) — **C-tier**
Reason: subset of KOL copy-trade. Whale = an entry in `KOLRegistry` with a different `tier` label. No new agent needed.

### MEV / Sandwich Bot — **C-tier**
Reason: out of scope. This is an execution-layer concern (transaction ordering), not a decision-layer one. Framework is decide-only.

---

## When to add a new strategy here

Before proposing one, answer all three:

1. **Distinct input shape** — does it need a context type that's not `TradingContext` / `KOLContext` / `GraduationContext` / `PositionContext`? If no, it's a config tweak on an existing agent, not a new strategy.
2. **Distinct signal** — what predictive feature does no existing agent already use as a *primary* trigger? "Already a scoring input" doesn't count.
3. **Boundary-safe** — can the framework define it without subscribing to a feed, holding state, or signing anything? If no, kill the proposal at the boundary.

If all three pass, file a design doc in [docs/plans/](plans/) (NOT `docs/superpowers/` — that path is retired). Reference this catalog from the spec.
