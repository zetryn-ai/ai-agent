# Agents Catalog

Single source of truth for every reference agent in this repo — shipped,
planned, and considered-and-rejected. Two categories so far:

- **Entry agent** — decides whether to OPEN a position (buy / skip / abort).
- **Position management agent** — decides what to do on an OPEN position
  (hold / take_profit / stop_loss / scale_out / exit_full).

For roadmap status see [CAPABILITIES.md §6](CAPABILITIES.md#6-roadmap).
For per-agent design specs see [plans/](plans/).
For non-roadmap changes see [maintenance-log.md](maintenance-log.md).

**Tier:** S = build next · A = build after S · B = considered, partial overlap · C = rejected with reason.

---

## Shipped

| Category | Name | Version | Builder | Modes | Distinct signal |
|---|---|---|---|---|---|
| Entry | Scanner | v0.1.0 / v0.3.0 | `build_scanner(llm)` | AI-first single LLM call + hard gates + guardrail | Multi-aspect narrative + structure analysis |
| Entry | Sniper | v0.1.0 / v0.11.0 (+reflect) | `build_sniper(llm?, decision_log?)` | rule · llm · hybrid · hybrid_audit | Sub-ms rule path; LLM inside deterministic guardrail |
| Entry | KOL Copy-Trade | v0.6.0 → v0.11.0 (K1–K7) | `build_kol_copytrade(pack, mode, ...)` | rule · confirmed · audit | Single-wallet historical performance (`KOLProfile`) + cooldown |
| Entry | Pump.fun Graduation Snipe | v0.12.0 | `build_graduation(llm?, decision_log?)` | rule · llm · hybrid · hybrid_audit | Bonding-curve fill speed + unique buyers + LP setup at graduation moment |

---

## Planned — S-tier (build next)

| Category | Name | Tier | Distinct signal | Why now |
|---|---|---|---|---|
| Position management | [PL1 — Position Lifecycle Helpers](#pl1-position-lifecycle-helpers) | S | PnL trajectory, drawdown-from-peak, time-in-trade on an open position | Biggest gap: every shipped agent decides ENTRY, nothing helps with EXIT. Users bolt on TP/SL outside the framework. |
| Entry | [S5 — Smart Money Confluence](#s5-smart-money-confluence) | S | N pre-vetted smart wallets converging on the same token within window T | Smart-wallet count is currently a scoring INPUT inside scanner. As primary trigger it's a much higher-precision signal. Distinct from KOL (multi-wallet correlation, not single-wallet copy). |

## Planned — A-tier (after S ships)

| Category | Name | Tier | Distinct signal | Why later |
|---|---|---|---|---|
| Entry | Migration Front-Run | A | Token migrating between DEXes (Raydium ↔ Meteora, pool upgrades). Not a new launch — has history, holders, narrative. | Smaller TAM than S-tier; depends on cross-DEX migration feed. |
| Entry | Re-Accumulation Detector | A | Post-dump (-60–80%) tightening sells + smart-wallet quiet accumulation + holder rebound | Especially benefits from PL1 lifecycle helpers — build that first. |

## Considered, NOT pursued (B / C-tier)

| Category | Name | Tier | Reason rejected |
|---|---|---|---|
| Entry | Volume Spike Scanner | B | Too easy to bait (wash-trading triggers same signal as organic momentum). Existing scanner already weights volume. No distinct primary signal. |
| Entry | Twitter Sentiment Pump | C | By the time sentiment lags into the framework, the move is done. Belongs as a scoring input (already in `SocialData`), not a trigger. |
| Entry | Whale Wallet Mirror (single whale) | C | Subset of KOL copy-trade — a whale is just a `KOLRegistry` entry with a `whale` tier. No new agent needed. |
| Execution | MEV / Sandwich Bot | C | Out of scope: execution-layer concern (transaction ordering). Framework is decide-only. |

---

## Detailed specs (S-tier)

### PL1 — Position Lifecycle Helpers

**Category:** Position management · **Tier:** S · **Status:** planned · **Spec:** TBD

**Boundary check (NON-NEGOTIABLE):** Returns *recommendations*. Bot owns the open position, live price stream, MEV, slippage, signing, persistence. Framework holds no position state across calls — bot pushes a fresh `PositionContext` per tick.

**Proposed shape:**

```python
class PositionState(BaseModel):
    entry_price: float
    entry_size: float
    current_price: float
    pnl_pct: float
    holding_seconds: float
    peak_pnl_pct: float
    drawdown_from_peak_pct: float

class LifecycleConfig(BaseModel):
    take_profit_pcts: list[float] = [0.5, 1.0, 3.0]   # scale-out ladder
    stop_loss_pct: float = -0.3
    trailing_drawdown_pct: float = 0.5
    max_hold_seconds: float = 3600
    decision_mode: Literal["rule", "llm", "hybrid"] = "rule"

@dataclass
class PositionContext:
    token: TokenInput
    position: PositionState
    config: LifecycleConfig = field(default_factory=LifecycleConfig)
```

Output: `Decision(action ∈ {hold, take_profit, stop_loss, scale_out, exit_full})` with `size` = how much to sell.

**Why distinct from entry agents:** different input shape (`PositionContext`), different output action space (sell-side ladder), different features (PnL trajectory, time-in-trade, drawdown-from-peak).

### S5 — Smart Money Confluence

**Category:** Entry · **Tier:** S · **Status:** planned · **Spec:** TBD

**Proposed shape:**

```python
class SmartWalletBuy(BaseModel):
    wallet: str
    sol_amount: float
    detected_at_ts: float

class SmartConfluenceEvent(BaseModel):
    mint: str
    buys: list[SmartWalletBuy]
    window_seconds: float
    first_buy_ts: float
    distinct_smart_wallets: int

class SmartConfluenceConfig(BaseModel):
    min_distinct_wallets: int = 3
    max_window_seconds: float = 120.0
    min_wallet_hit_rate: float = 0.5
    require_no_bundler_overlap: bool = True
    decision_mode: Literal["rule", "llm", "hybrid", "hybrid_audit"] = "rule"
```

Reuses sniper's `fast_safety` + a generalized `market_gate`. New `SmartWalletRegistry` (parallel to `KOLRegistry`, sourced from `KnowledgePack`).

**Why distinct from KOL Copy-Trade:** KOL = single-wallet copy. Confluence = multi-wallet correlation (cluster of independent smart wallets converging). Different trigger semantics, different config (min_distinct_wallets, window), different failure modes (one rogue wallet doesn't fire S5).

---

## Three-question gate for proposing any new agent

Before drafting a spec, answer all three. Fail one → don't propose.

| # | Question | Fail = |
|---|---|---|
| 1 | **Distinct input shape** — needs a context not in `{TradingContext, KOLContext, GraduationContext, PositionContext}`? | Config tweak on existing agent, not a new agent |
| 2 | **Distinct primary signal** — predictive feature no existing agent uses as primary trigger? "Already a scoring input" doesn't count. | Add as scoring input to existing agent |
| 3 | **Boundary-safe** — framework can define it without subscribing, holding state, or signing? | Kill at the boundary — that's a bot-layer concern |

If all three pass: file a spec in [docs/plans/](plans/) (NOT `docs/superpowers/` — retired) and add a row to the appropriate table above.
