**Date:** 2026-06-27
**Status:** Shipped (v0.16.0)

# A1 — Organic Growth Detector

## 0. Summary

A **triage filter** — not a buy agent. Classifies a token's post-launch
time-series as `organic`, `suspicious`, or `manipulated` based on
chart-pattern features. The verdict promotes or demotes scanner candidates
before a full entry decision is made.

Core insight: organic growth = **steady climb + healthy pullbacks + rising
unique-buyer count**. Manipulation tell = **vertical line with near-zero
sells** (coordinated pump, no real demand). These patterns are derivable
from 5–15 minutes of candle data and are detectable before the dump phase.

Validated as A-tier (not S): the signal narrows the window for a specific
chart shape and requires a meaningful observation period, making it more
useful as a pre-filter than a standalone entry trigger.

## 1. Boundary recap

| Layer | Responsibility |
|---|---|
| Bot | Watches candle/trade stream (Helius/GMGN/Cielo), computes aggregate signals over the observation window, fills `GrowthSnapshot`, pushes `GrowthContext` |
| Framework | Validates observation completeness, detects manipulation patterns, scores organic signals, returns `Decision` with classification |

The framework never aggregates candles or accesses price history.

## 2. Integration pattern

This agent returns `Decision(action=…)` with the following mapping:

| `action` | Meaning | Bot behaviour |
|---|---|---|
| `"buy"` | Classified **organic** — promote | Run full scanner / boost confidence |
| `"skip"` | **Suspicious** — ambiguous signals | Normal scanner flow, no promotion |
| `"abort"` | Clear **manipulation** — demote | Skip scanner, add to cooldown |

`Decision.flags["classification"]` carries the string `"organic"` /
`"suspicious"` / `"manipulated"` for explicit logging. `Decision.scores`
carries the `organic_score` for calibration.

## 3. Schemas (`trading/schemas.py`)

### `GrowthSnapshot`
Aggregate features the bot computes from its candle/trade stream.

| Field | Type | Notes |
|---|---|---|
| `mint` | `str` | |
| `detected_at_ts` | `float` | Snapshot time |
| `observation_seconds` | `float` | How long we've observed |
| `candle_count` | `int` | Number of completed candles |
| `price_trajectory` | `Literal[…]` | `"steady_climb"` / `"vertical_pump"` / `"volatile"` / `"flat"` / `"declining"` |
| `sell_presence_pct` | `float [0,1]` | Fraction of candles with meaningful sell volume (< 0.02 = suspicious zero-sell) |
| `unique_buyer_trend` | `float [-1,1]` | Positive = new buyers joining |
| `holder_growth_rate` | `float` | New holders per minute |
| `has_healthy_pullback` | `bool` | At least one meaningful dip + recovery |
| `max_drawdown_pct` | `float [0,1]` | Worst intra-window pullback (organic = 0.05–0.25) |
| `whale_volume_pct` | `float [0,1]` | Volume fraction from whale wallets |
| `volume_acceleration` | `float` | recent_volume / early_volume (> 1.5 = accelerating) |

### `GrowthConfig`

| Field | Default | Notes |
|---|---|---|
| `decision_mode` | `"rule"` | rule / llm / hybrid / hybrid_audit |
| `min_observation_seconds` | `120.0` | Need ≥ 2 min of history |
| `min_candle_count` | `5` | Need ≥ 5 candles |
| `min_sell_presence_pct` | `0.03` | < this = zero-sell manipulation flag |
| `max_sell_presence_pct` | `0.70` | > this = excessive dumping |
| `min_unique_buyer_trend` | `-0.20` | Strongly falling buyers → suspicious |
| `max_whale_volume_pct` | `0.65` | > this → whale-dominated |
| `organic_score_threshold` | `0.65` | Score ≥ this → organic (buy) |
| `suspicious_score_threshold` | `0.35` | Score ≥ this → suspicious (skip); below → manipulated (abort) |

### `GrowthContext`
`token: TokenInput`, `snapshot: GrowthSnapshot`, `config: GrowthConfig`

### `GrowthVerdict`
LLM structured output: `classification ∈ {organic, suspicious, manipulated}`,
`confidence`, `promote_scanner`, `signals[]`, `reasoning`.

## 4. Graph design

```
fast_safety → observation_gate → manipulation_gate → organic_classify → END
(llm/hybrid) → [reflect?] → growth_llm → END
(hybrid_audit) → organic_classify → audit_dispatch → END
```

### Nodes

| Node | Purpose |
|---|---|
| `fast_safety` | Reuse `sniper_nodes.fast_safety` |
| `observation_gate` | Enough candles + observation time; rejects "too early" |
| `manipulation_gate` | Hard abort: `vertical_pump` + zero sells, or extreme whale dominance |
| `organic_classify` | Score 5 organic signals → classify → emit `Decision` |
| `growth_prompt` / `growth_result` / `growth_guardrail` | LLM path |
| `make_audit_dispatch` | Async audit |

### Organic scoring (rule mode)

Five equally-weighted dimensions (0.2 each):

| Dimension | Organic condition |
|---|---|
| Price trajectory | `steady_climb` or `volatile` (not vertical / flat / declining) |
| Sell presence | `min_sell_pct ≤ sell_presence_pct ≤ max_sell_pct` |
| Buyer trend | `unique_buyer_trend ≥ min_unique_buyer_trend` |
| Pullback quality | `has_healthy_pullback is True` |
| Whale balance | `whale_volume_pct ≤ max_whale_volume_pct` |

`organic_score = sum(0.2 for each passing dimension)`

Classification:
- `organic_score ≥ organic_score_threshold (0.65)` → `"buy"` (promote)
- `organic_score ≥ suspicious_score_threshold (0.35)` → `"skip"` (neutral)
- below → `"abort"` (manipulated, demote)

## 5. Open questions resolved

All design decisions settled at spec time.
