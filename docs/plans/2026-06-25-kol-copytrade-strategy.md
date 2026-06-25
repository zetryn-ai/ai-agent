# KOL Copy-Trade — Strategy Design

**Date:** 2026-06-25
**Status:** K1-K4 shipped in **v0.6.0** (2026-06-25). K5-K8 pending. Boundary recap (§0.5) and locked decisions (§15, §16) remain authoritative.
**Target milestone:** new strategy reference agent in `strategies/agents/kol_copytrade.py`
**Foundations relied on:** F1 (`KnowledgePack`), F2 (`ReflectiveNode`), F3 (`LLMRouter`), tool-use loop (v0.5.0), `AgentNode`

---

## 0. Why this doc exists

After v0.5.0 the framework has all primitives needed for a first real
strategy: tool-use loop, knowledge injection, multi-provider routing,
reflective learning. The reference scanner + sniper are still **generic** —
they classify and execute but do not encode an entry hypothesis. This
document specifies the first strategy that **does** encode a hypothesis,
chosen because it is (a) marketable, (b) data-ready in the schema, and
(c) representative of the broader pattern we want to formalise.

---

## 0.5 Framework boundary recap (the rules this doc lives within)

Zetryn Trading is an **AI Agent Framework / library** that public users
consume from inside their own bots. Restated to prevent scope creep
inside this strategy:

| Framework does | Bot (user code) does |
|---|---|
| Define the input/output schemas | Fetch / stream the data and fill the schemas |
| Orchestrate the decision graph | Subscribe to Helius / Cielo / GMGN / WS feeds |
| Run LLM analyst calls + tool-use loops | Implement the actual tool functions (`async def check_rug`, `async def kol_recent_performance`, …) |
| Read `KnowledgePack` files | Author + maintain those files (KOL whitelists, rules) |
| Read `DecisionLog` for reflection | Write outcomes back via `record_outcome` after execution |
| Return a `Decision` (action, size, reasons) | Execute the trade, sign tx, manage position lifecycle |

This strategy adds **no exception** to those rules. Every "the strategy
needs data X" below is shorthand for "the framework defines the shape
of X; the bot supplies it". If a section ever reads otherwise, it's a
documentation bug — flag it.

---

## 1. The hypothesis (in one paragraph)

> Certain Solana wallets — "KOLs" — have a measurable historical edge on
> memecoin entries. When such a wallet buys a new token within a short
> window (typically <5 minutes since launch), the probability of a
> profitable follow-on trade exceeds the base rate by a margin worth
> trading on, **provided** the token also passes structural safety
> filters (no honeypot, dev not previously rug-history) and shows no
> obvious bundler / sniper-coordinated front-running.

Edge degrades fast: the value of the signal is highest in the seconds
immediately after the KOL buy and decays within minutes as price moves.
That latency budget shapes the entire architecture.

---

## 2. Precise definition of "copy-trade" here

To prevent scope creep:

- **In scope:** react to *individual* KOL wallet buy events with a
  size-bounded entry decision. Exit logic stays in the bot (this
  strategy emits entries, not full trade lifecycles).
- **Out of scope:** mirroring an entire wallet's portfolio, position
  sizing as a percentage of the KOL's own position, or following
  sell signals. These are valid extensions but not v1.

---

## 3. Trigger pattern — still pull, semantically push

The library's call shape does NOT change: the bot always calls
`agent.run(State(context=...))`. What changes is **what the bot pushes
into the context** and **when the bot makes that call**.

For scanner/sniper, bot calls the agent whenever it has a token
candidate. For copy-trade, the bot calls the agent whenever it receives
a KOL wallet buy event — but framework-side, it's still the same
synchronous call returning a `Decision`.

```
Bot side (NOT framework):
    helius/cielo WS  ── KOL wallet buy event ──┐
                                                v
                              build KOLContext(event=..., token=...)
                                                v
                                                                 ┌─────────────────────┐
                                  decision = kol_copytrade.run() ──> ZETRYN FRAMEWORK  │
                                                v                │ runs decision graph │
                                          bot executes           └─────────────────────┘
```

The framework provides:
- The `KOLContext` schema (so the bot knows what to fill).
- The `build_kol_copytrade(...)` graph (the decision logic).

The framework does NOT subscribe to anything, does NOT fetch token
data, does NOT identify which wallet is a KOL. All of that is bot
work that produces the `KOLContext` argument.

---

## 4. Schemas the framework defines (and the bot fills)

These ship in `trading/schemas.py`. **The framework only defines them.**
Anything that populates them is bot work.

```python
class KOLBuyEvent(BaseModel):
    """A KOL wallet just bought a token. Built by the BOT from its
    event stream (Helius webhook, Cielo subscription, custom indexer)."""
    wallet: str                       # KOL wallet address
    mint: str                         # token they bought
    sol_amount: float                 # size of KOL's buy in SOL
    detected_at_ts: float             # unix ts when bot saw the event
    block_age_seconds: float          # how stale this signal already is


class KOLContext(BaseModel):
    """The input the bot hands to build_kol_copytrade(...)."""
    event: KOLBuyEvent
    token: TokenInput                 # bot-enriched, same shape scanner uses
    config: KOLCopyTradeConfig
```

The bot's responsibilities (NOT framework work):
1. Subscribe to KOL wallet activity.
2. Build the `TokenInput` for the bought mint (same enrichment path
   the bot already uses for scanner inputs).
3. Construct `KOLBuyEvent` + `KOLContext` and pass to the framework.
4. Execute the returned `Decision`.

The framework's responsibility: validate the schemas exist, run the
decision graph against the populated context, return a `Decision`.

---

## 5. Architecture (graph)

```
fast_safety  (rule, <1ms)        ← honeypot, freeze auth, dev rug history
       │
       v
kol_quality  (rule, <1ms)        ← look up wallet hit-rate / avg pnl from KnowledgePack
       │                            (filter: kol must clear min hit-rate threshold)
       v
fast_market  (rule, <1ms)        ← min liquidity, max bundler/sniper count
       │
       v
analyst      (LLM, 200-500ms)    ← optional, only in `confirmed` mode (see §7)
       │                            uses ToolUseNode so it can pull more data
       v
sizing       (rule, <1ms)        ← size = base × kol_confidence × token_safety
       │
       v
Decision { action="buy"|"skip"|"abort", size, confidence, reasons }
```

**Reuses existing components:**
- `fast_safety`, `fast_market` lifted from sniper (already battle-tested).
- `analyst` reuses `make_analyst_prompt(pack)` factory if used.
- `KnowledgePack.lookup("kol_whitelist", wallet_address)` for KOL profile.
- `ReflectiveNode` optional — feeds past KOL-copytrade losses back.

**What's new:**
- `kol_quality` rule node (small, deterministic).
- `KOLBuyEvent`, `KOLContext`, `KOLCopyTradeConfig` schemas.
- One Tool: `kol_recent_performance(wallet)` for the analyst to use in
  `confirmed` mode.

---

## 6. KnowledgePack contents for KOLs

```
my-pack/
├── system/
│   └── 01-copytrade-rules.md       # natural-language KOL playbook
└── data/
    └── kol_whitelist.json           # structured per-wallet profile
```

`kol_whitelist.json` shape (proposed):
```json
{
  "wallets": {
    "Abc...123": {
      "name": "smart_money_1",
      "hit_rate": 0.52,
      "avg_pnl_pct": 0.38,
      "trades_30d": 47,
      "exit_pattern": "scales_out_50pct",
      "tier": "S",
      "min_sol_to_copy": 0.5
    }
  },
  "min_tier_to_copy": "A",
  "min_hit_rate": 0.40
}
```

The bot maintains this file (computed offline from on-chain history,
or imported from Cielo / GMGN). The framework just reads it.

---

## 7. Decision modes (mirrors sniper)

To keep this composable, the strategy supports the same mode pattern as
the sniper:

| Mode | Path | Latency | When to use |
|---|---|---|---|
| `rule` (default) | pure rule chain, no LLM | < 1 ms | live, latency-critical |
| `confirmed` | rule chain → `analyst` LLM final check | 200-500 ms | tokens older than 60s, when latency budget allows |
| `audit` | rule decides instantly + LLM verifies async | < 1 ms + bg task | learn-while-trading mode |

Same pattern as `SniperConfig.decision_mode`. Default is `rule` because
KOL signals decay in seconds.

---

## 8. Sizing logic (new piece)

`base_size × kol_confidence × token_safety_multiplier`, all clamped to
`max_size`. Concretely:

```python
kol_confidence = clamp(kol_profile["hit_rate"], 0.4, 0.7) - 0.4   # 0..0.3 range
token_safety = 1.0 - max(0, top10_pct - 0.20)                     # penalty over 20%
size_sol     = cfg.base_size * (1.0 + 2.0 * kol_confidence) * token_safety
size_sol     = clamp(size_sol, 0, cfg.max_size)
```

Numbers are placeholders; tuning is calibration work, not design.

---

## 9. Optional tools the analyst can use (framework defines, bot implements)

When in `confirmed` mode, the analyst's tool-use loop has access to
whatever `Tool`s the bot has registered. The framework ships **the
expected input schema and a stub example** for one canonical tool, the
bot ships **the actual implementation**:

```python
# Framework ships this schema in a reference module (e.g. strategies/tools.py)
class KOLPerfInput(BaseModel):
    wallet: str
    lookback: int = Field(default=20, ge=1, le=200)

# Framework documents the expected behaviour:
#   "Look up a KOL wallet's win rate and average PnL over the last N trades.
#    Return shape: {hit_rate: float, avg_pnl_pct: float, sample_size: int}"

# Bot wires the actual function:
async def kol_recent_performance(wallet: str, lookback: int = 20) -> dict:
    # Bot's data source — Cielo, GMGN, custom indexer, the bot's own DB.
    return await my_indexer.kol_stats(wallet, lookback)

registry.register(Tool("kol_recent_performance",
                       "...",
                       kol_recent_performance,
                       input_schema=KOLPerfInput))
```

This is the **first real tool integration pattern**. The framework
proves the wiring end-to-end with a stub implementation in the example
folder; production users plug in their own data source. The same
pattern applies to every future tool (`check_rug`, `get_holder_pnl`,
`fetch_twitter_velocity`, etc.).

---

## 10. What the framework does NOT do

To make the boundary unambiguous, repeated here:

- ❌ Watch KOL wallets (bot subscribes to WS / webhook)
- ❌ Maintain the KOL whitelist (bot computes offline, ships as KnowledgePack)
- ❌ Score KOL hit-rate or PnL (bot computes offline from on-chain history)
- ❌ Enrich `TokenInput` (bot uses Helius / Birdeye / GMGN / DexScreener)
- ❌ Implement any `Tool` function — the framework defines schemas,
  the bot wires the async function (data source agnostic)
- ❌ Track positions / portfolio
- ❌ Execute orders, sign transactions, manage slippage
- ❌ Trigger itself periodically — every run is initiated by the bot

The framework decides whether the buy is justified and at what size,
given everything the bot pushed in. That is the entire contribution.

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| KOL is itself a pump-and-dump operator using you as exit liquidity | KOL tier filter + `exit_pattern` metadata; only follow KOLs whose historical exits avoid dumping into followers. Tracked in `kol_whitelist.json`. |
| Signal latency too high → KOL already pumped the token | `block_age_seconds` field on `KOLBuyEvent`; `kol_quality` node rejects when stale (default >30s). |
| Whitelist gets stale, KOL stops being profitable | `ReflectiveNode` integration: bot calls `decision_log.record_outcome` after exit; reflect node surfaces "wallet X turned losing" patterns to analyst. Whitelist refresh stays bot-side. |
| Snipers + bundlers front-running the same signal | `fast_market` node uses `wallets.sniper_wallet_count` / `bundler_wallet_count` thresholds (same as sniper). |
| KOL whitelist contains fake or low-quality entries | Validation at `KnowledgePack.from_dir` time: warn on missing required fields per profile (`hit_rate`, `tier`); reject if `min_hit_rate < hit_rate` is malformed. |
| User has no KOL whitelist | Graceful fallback: with no whitelist, `kol_quality` rejects all → action="skip". Bot operator sees "no KOLs configured" in reasons. |

---

## 12. Acceptance criteria

The strategy is considered done when:

1. `build_kol_copytrade(...)` exists in `strategies/agents/kol_copytrade.py`
   and returns a compiled `Graph` accepting `State(context=KOLContext(...))`.
2. With a stub LLM and a stub `KnowledgePack`, the graph produces sensible
   decisions for a synthetic event set covering: trusted KOL + safe token
   → `buy`; trusted KOL + rug → `abort`; unknown wallet → `skip`; stale
   signal → `skip`.
3. `Decision` carries the `kol_profile` it acted on in `reasons` for
   auditability.
4. Mode switch works: `rule` mode produces a decision in <1ms with no
   LLM call; `confirmed` mode runs the analyst tool-use loop.
5. Integration with `ReflectiveNode` documented and exercised in at least
   one test (past KOL-copytrade losers surface in the analyst's prompt).
6. New tests in `tests/test_kol_copytrade.py` — ≥10 cases — all pass; no
   regression in existing 162 tests.
7. Example `examples/run_kol_copytrade.py` runs end-to-end with stub LLM
   and a hand-written `KnowledgePack`.
8. Documentation: README has a "Three reference agents" framing now
   (Scanner / Sniper / KOL Copy-Trade); CAPABILITIES.md §6 roadmap
   updated.

---

## 13. Implementation phases (proposed milestone breakdown)

Each phase ships independently and is testable in isolation.

| Phase | Focus | Estimated effort |
|---|---|---|
| **K1** | Schemas: `KOLBuyEvent`, `KOLContext`, `KOLCopyTradeConfig`, `KOLProfile` in `trading/schemas.py` | Small |
| **K2** | `KOLRegistry` helper on top of `KnowledgePack` for typed lookup; tests | Small |
| **K3** | `kol_quality` rule node + `sizing` rule node + tests | Small |
| **K4** | `build_kol_copytrade(llm=None, knowledge_pack=...)` graph wiring (`rule` mode only) + tests | Medium |
| **K5** | Add `confirmed` mode: integrate `ToolUseNode` with `kol_recent_performance` tool; tests | Medium |
| **K6** | Add `audit` mode (mirror sniper hybrid_audit pattern); tests | Small |
| **K7** | Integrate `ReflectiveNode` (when `decision_log` provided); tests | Small |
| **K8** | Example `examples/run_kol_copytrade.py`; README + CAPABILITIES.md updates | Small |

Could ship K1-K4 as a first release (v0.6.0), then K5-K7 as v0.7.0
once `rule` mode is proven. K8 piggybacks on whichever release closes
the strategy.

---

## 14. Out of scope (parked for later)

- Exit decisions (take profit, stop loss, trailing) — bot owns trade
  lifecycle.
- Position sizing relative to KOL's own position size (would need a
  live portfolio mirror, much bigger scope).
- Multi-KOL confluence (e.g. "buy only when ≥2 trusted KOLs hit the
  same mint within 60s") — easy follow-up once single-KOL works.
- Automatic KOL discovery / scoring — that's the bot's offline pipeline.
- Yield-from-fees or LP-side strategies.

These are all valid future work but **none** is required to prove the
strategy pattern.

---

## 15. Locked decisions (resolved 2026-06-25)

| # | Question | Decision |
|---|---|---|
| 1 | Default mode in first release? | **`rule` only.** Ship K1–K4 as v0.6.0; `confirmed` (with tool-use loop) follows as v0.7.0, `audit` after that. |
| 2 | Sizing formula — hardcoded or in config? | **In `KOLCopyTradeConfig` from day one.** The config carries `base_size`, `max_size`, `kol_confidence_floor`, `kol_confidence_ceiling`, `top10_penalty_start`. The formula in `sizing` node reads these. |
| 3 | Whitelist source format? | **JSON only** (`kol_whitelist.json`). Consistent with existing `KnowledgePack` pattern. CSV importer can be a 10-line follow-up if any user asks. |
| 4 | Cool-down between repeated copies of same KOL? | **Yes, configurable.** `kol_cooldown_seconds=60` default on `KOLCopyTradeConfig`. The cool-down state is held by the *bot* (framework is stateless across runs); framework just exposes the field and the `kol_quality` node checks `event.detected_at_ts` against an optional `last_copy_ts_by_kol` field the bot can populate inside `KOLContext`. |

### Implementation consequence of #4 (cooldown)

To keep the framework stateless, `KOLContext` will carry an optional
`last_copy_ts` (when this same KOL was last copied by this bot). The
`kol_quality` node enforces the cooldown using that value. Bot owns
the state, framework owns the rule. Schema field:

```python
class KOLContext(BaseModel):
    event: KOLBuyEvent
    token: TokenInput
    config: KOLCopyTradeConfig
    last_copy_ts: float | None = None   # bot-provided; None = no recent copy
```

---

## 16. First release scope (v0.6.0)

Locked: ship **K1 + K2 + K3 + K4** in v0.6.0.

- ✅ Schemas (K1)
- ✅ `KOLRegistry` helper (K2)
- ✅ `kol_quality` + `sizing` rule nodes (K3)
- ✅ `build_kol_copytrade(llm=None)` `rule`-mode graph + tests + example (K4)

Deferred to later releases:
- v0.7.0: K5 (`confirmed` mode with tool-use)
- v0.8.0: K6 (`audit` mode) + K7 (`ReflectiveNode` integration)
- v0.9.0: K8 (docs polish — README "three reference agents" framing)
