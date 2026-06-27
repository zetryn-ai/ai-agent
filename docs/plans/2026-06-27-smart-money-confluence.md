**Date:** 2026-06-27
**Status:** Shipped (v0.14.0)

# S5 — Smart Money Confluence Strategy

## 0. Summary

Fire a buy signal when **≥ N pre-vetted smart wallets have accumulated the same token within a rolling window**. Multi-wallet correlation is the primary signal — much higher precision than copying any one wallet because independent actors must converge on the same thesis.

Validated as a mainstream 2026 Solana pro strategy: DEXTools and Cielo both surface "5+ smart wallets scooping a token over a week" as a high-conviction entry trigger. Distinct from KOL copy-trade (single-wallet social signal) and from the scanner (point-in-time snapshot, not behaviour correlation).

---

## 1. Boundary recap

| Layer | Responsibility |
|---|---|
| Bot | Subscribes to wallet feeds (Cielo, GMGN, Helius), aggregates per-mint accumulations per rolling window, fills `ConfluenceEvent`, pushes `ConfluenceContext` per signal |
| Framework | Reads the event, validates confluence thresholds, evaluates token quality, sizes and returns `Decision` |

The framework never opens a socket, tracks positions, or signs anything.

---

## 2. Schemas (`trading/schemas.py`)

### `SmartWalletProfile`
Per-wallet historical performance, bot-computed offline and shipped in `KnowledgePack` as `data/smart_wallet_whitelist.json`. Analogous to `KOLProfile` but represents anonymous on-chain wallets tracked by profitability only — no social identity, no exit-pattern label.

| Field | Type | Notes |
|---|---|---|
| `hit_rate` | `float [0,1]` | Win rate across tracked trades |
| `avg_pnl_pct` | `float` | Average realised PnL % |
| `trades_30d` | `int` | Activity proxy |
| `tier` | `Literal["S","A","B","C"]` | Bot-assigned tier |
| `min_sol_to_copy` | `float` | Ignore accumulations below this size |

### `SmartWalletAccumulation`
One wallet's buy inside the rolling window, built by the bot.

| Field | Type | Notes |
|---|---|---|
| `wallet` | `str` | On-chain address |
| `mint` | `str` | Token accumulated |
| `sol_amount` | `float` | Size of the buy |
| `detected_at_ts` | `float` | Bot's detection timestamp (unix) |
| `block_age_seconds` | `float` | How stale this individual signal is |

### `ConfluenceEvent`
Aggregated confluence snapshot the bot pushes per detected signal.

| Field | Type | Notes |
|---|---|---|
| `mint` | `str` | Token with multi-wallet accumulation |
| `detected_at_ts` | `float` | When confluence was detected |
| `window_seconds` | `float` | Rolling window used (informational) |
| `accumulations` | `list[SmartWalletAccumulation]` | All contributing buys in the window |

Framework computes derived stats (unique wallet count, total SOL, average quality) from this list — no pre-aggregation required from the bot.

### `ConfluenceConfig`

| Field | Default | Notes |
|---|---|---|
| `decision_mode` | `"rule"` | rule / llm / hybrid / hybrid_audit |
| `min_wallet_count` | `5` | Minimum distinct smart wallets required |
| `min_sol_per_wallet` | `0.5` | Reject accumulations smaller than this |
| `max_signal_age_seconds` | `60.0` | Freshness of the most-recent accumulation |
| `min_hit_rate` | `0.35` | Per-wallet quality floor |
| `min_tier` | `"B"` | Per-wallet tier floor |
| `min_liquidity_usd` | `3_000` | Market gate |
| `min_volume_1h` | `0.0` | Market gate |
| `max_top10_pct` | `0.6` | Holder concentration |
| `max_bundler_wallets` | `3` | Bundler density |
| `max_sniper_wallets` | `15` | Sniper density |
| `base_size` | `1.0` | SOL base bet |
| `max_size` | `5.0` | Hard cap |

### `ConfluenceContext`
`token: TokenInput`, `event: ConfluenceEvent`, `config: ConfluenceConfig`

### `ConfluenceVerdict`
LLM structured output: `action ∈ {buy, skip, abort}`, `confidence`, `size_pct`, `reasoning`, `concerns[]`.

---

## 3. SmartWalletRegistry (`strategies/smart_wallet_registry.py`)

Mirrors `KOLRegistry` pattern. Loads `smart_wallet_whitelist.json` from a `KnowledgePack`:

```json
{
  "wallets": { "<address>": { ...SmartWalletProfile fields... } },
  "min_tier_to_use": "B",
  "min_hit_rate": 0.35
}
```

Exposes `get(wallet)`, `passes_global_floor(profile)`, `min_tier`, `min_hit_rate`.

---

## 4. Graph design

```
fast_safety → confluence_gate → market_gate → rule_size_and_buy → END
                                              ↘ (llm/hybrid) [reflect?] → confluence_decide → END
                                              ↘ (hybrid_audit) → rule_buy → audit_dispatch → END
```

### Nodes

| Node | Purpose |
|---|---|
| `fast_safety` | Reuse `sniper_nodes.fast_safety` — instant contract abort |
| `confluence_gate` | Unique wallet count, per-wallet quality (tier, hit_rate, sol_amount), signal freshness |
| `market_gate` | Liquidity, volume, top10_pct, bundler/sniper density |
| `rule_size_and_buy` | `base × wallet_mult × quality_mult`, capped at `max_size` |
| `confluence_prompt` | Narrative for LLM analyst |
| `confluence_result` | `ConfluenceVerdict → Decision` converter |
| `confluence_guardrail` | Hybrid hard rails (rug → abort, size cap) |
| `make_audit_dispatch` | Async `AuditVerdict` background task |

### Sizing formula (rule mode)

```
unique_count    = len({a.wallet for a in event.accumulations that passed quality gate})
wallet_mult     = clamp(unique_count / min_wallet_count, 1.0, 2.0)
avg_hit_rate    = mean(profile.hit_rate for qualifying wallets)
quality_mult    = 0.6 + 0.4 * clamp((avg_hit_rate - 0.35) / 0.35, 0, 1)
top10_penalty   = 1 − max(0, top10_pct − 0.2)
size            = clamp(base_size × wallet_mult × quality_mult × top10_penalty, 0, max_size)
```

---

## 5. Decision modes

Identical contract to graduation snipe:

| Mode | Description |
|---|---|
| `rule` | Pure rule path, sub-ms |
| `llm` | Gates → [reflect?] → LLM decide |
| `hybrid` | LLM + deterministic guardrail (rug/size cap) |
| `hybrid_audit` | Rule decides instantly; async LLM audit fires in background |

---

## 6. Open questions resolved

All design decisions settled at spec time — no open questions.
