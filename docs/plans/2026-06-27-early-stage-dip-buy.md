**Date:** 2026-06-27
**Status:** Shipped (v0.15.0)

# S6 — Early-Stage Dip Buy

## 0. Summary

One agent, two events. After a Solana memecoin launches or graduates, an
initial dump wave always follows (snipers/bundlers selling for launch;
early-BC buyers taking profit for graduation). S6 waits for that dump
to **settle** and enters when sell pressure thins out, holders retain,
and the unique-buyer count starts recovering.

`event_type ∈ {launch, graduation}` in config selects the timing window
and threshold defaults; the signal mechanic is the same for both.

Validated as mainstream 2026 Solana pro strategy: multiple trading desks
describe "buying the 1–10 min dip after launch" and "buying the post-grad
TP wave" as high-conviction setups when paired with holder-retention and
buy-ratio filters (Cielo, GMGN, DEXTools community).

**Distinct from:**
- Speed sniper — fires immediately at launch, no waiting for dump to settle.
- Graduation snipe — fires in the 5–30s window *at* graduation (before the TP
  wave starts), not after.

---

## 1. Boundary recap

| Layer | Responsibility |
|---|---|
| Bot | Monitors token post-event (Helius/Cielo/GMGN), samples sell/buy flow, computes holder snapshot, pushes `DipBuyContext` when it detects possible settlement |
| Framework | Validates timing window, checks dip depth + sell-pressure subsiding + recovery signals, sizes buy, returns `Decision` |

The framework never opens a socket, aggregates candles, or signs anything.

---

## 2. Schemas (`trading/schemas.py`)

### `DipBuySnapshot`
Per-check snapshot the bot pushes. Bot owns the time-series; framework only reads this.

| Field | Type | Notes |
|---|---|---|
| `event_type` | `Literal["launch", "graduation"]` | Selects threshold defaults |
| `mint` | `str` | Token address |
| `detected_at_ts` | `float` | When this snapshot was taken |
| `time_since_event_seconds` | `float` | Seconds since launch / graduation |
| `price_vs_ath_pct` | `float` | Current price vs post-event ATH, as % (negative = dipped below ATH) |
| `sell_pressure_score` | `float [0,1]` | Bot-computed: 0=no sells, 1=extreme selling |
| `buy_ratio_5m` | `float [0,1]` | buys/(buys+sells) last 5 min |
| `holder_retention_pct` | `float [0,1]` | Fraction of holders that stayed through the dump |
| `unique_buyers_trend` | `float [-1,1]` | Positive=unique buyers rising, negative=falling |
| `price_stable_seconds` | `float` | How long the price has been stable (not making new lows) |

### `DipBuyConfig`

| Field | Default | Notes |
|---|---|---|
| `event_type` | `"launch"` | Must match `DipBuySnapshot.event_type` |
| `decision_mode` | `"rule"` | rule / llm / hybrid / hybrid_audit |
| `min_time_since_event_seconds` | `60.0` (launch) / `60.0` (grad) | Too early = dump still live |
| `max_time_since_event_seconds` | `600.0` (launch) / `1800.0` (grad) | Too late = window closed |
| `min_dip_pct` | `0.15` | Must have dipped at least 15% from ATH |
| `max_sell_pressure_score` | `0.35` | Gate: selling must have thinned out |
| `min_buy_ratio_5m` | `0.52` | Gate: buys overtaking sells |
| `min_holder_retention_pct` | `0.65` | Gate: holders held through dump |
| `min_unique_buyers_trend` | `0.0` | Gate: flat or rising (≥ 0) |
| `min_price_stable_seconds` | `30.0` | Gate: price not making new lows |
| `min_liquidity_usd` | `3_000` | Market gate |
| `max_top10_pct` | `0.65` | Market gate |
| `max_bundler_wallets` | `3` | Market gate |
| `max_sniper_wallets` | `15` | Market gate |
| `base_size` | `0.75` | Lower than sniper — higher uncertainty |
| `max_size` | `3.0` | |

### `DipBuyContext`
`token: TokenInput`, `snapshot: DipBuySnapshot`, `config: DipBuyConfig`

### `DipBuyVerdict`
LLM structured output: `action ∈ {buy, skip, abort}`, `confidence`, `size_pct`, `reasoning`, `concerns[]`.

---

## 3. Graph design

```
fast_safety → timing_gate → dip_gate → recovery_gate → market_gate →
    rule_size_and_buy → END
    (llm/hybrid) [reflect?] → dip_decide → END
    (hybrid_audit) → rule_buy → audit_dispatch → END
```

### Nodes

| Node | Purpose |
|---|---|
| `fast_safety` | Reuse `sniper_nodes.fast_safety` |
| `timing_gate` | `time_since_event` in `[min, max]` window; rejects "too early" and "too late" |
| `dip_gate` | Price dipped ≥ `min_dip_pct` from ATH; sell pressure ≤ threshold |
| `recovery_gate` | `buy_ratio_5m`, `holder_retention_pct`, `unique_buyers_trend`, `price_stable_seconds` |
| `market_gate` | Standard: liquidity, top10, bundler/sniper density |
| `rule_size_and_buy` | Size on recovery strength |
| `dip_prompt` / `dip_result` / `dip_guardrail` | LLM path |
| `make_audit_dispatch` | Async `AuditVerdict` |

### Sizing formula (rule mode)

```
recovery_score  = (buy_ratio_5m + holder_retention_pct + (unique_buyers_trend + 1) / 2) / 3
dip_bonus       = clamp((|price_vs_ath_pct| - min_dip_pct) / 0.30, 0, 1)  # deeper dip = more upside
sell_calm       = 1 - sell_pressure_score                                   # less selling = better entry
size            = clamp(base × recovery_score × (1 + 0.5 × dip_bonus) × sell_calm, 0, max)
```

---

## 4. Decision modes

Identical contract to all other entry agents: `rule` / `llm` / `hybrid` / `hybrid_audit`.

---

## 5. Open questions resolved

All design decisions settled at spec time.
