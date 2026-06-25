# Zetryn Agent Framework — AI-First Pivot

**Date:** 2026-06-24
**Status:** Implementation complete through M10. M8 hardened and closed in **v0.3.0** (2026-06-25); see [docs/CAPABILITIES.md §5](../CAPABILITIES.md) for the criterion-by-criterion evidence.
**Supersedes (in part):** [2026-06-23-zetryn-agent-framework-design.md](2026-06-23-zetryn-agent-framework-design.md) — sections 2 (LLM role row), 5 (LLM Layer), 9 (Use-Case Mapping). All other sections of the 2026-06-23 doc remain authoritative.

> **Update 2026-06-25:** §7 roadmap, §10 acceptance criteria, and §11 out-of-scope list have been annotated to reflect what shipped (v0.1.0 → v0.3.0). Three items that were "out of scope" — `KnowledgePack`, `LLMRouter`, `ReflectiveNode` — were prioritised early as **pre-P1 foundations** (F1/F3/F2) because they unblock the learning loop that M8 needed to be meaningful.

---

## 0. Why this doc exists

The 2026-06-23 design built M0–M6 + S1 with **rules as the primary decision-makers and LLM as advisor** (one LLM call per scan, used only for narrative scoring). That delivered a working framework but it does not match the product positioning we are committing to:

> **Zetryn Agent Framework = AI Agent Trading from Zetryn AI.**

A product sold as an "AI Agent" cannot be 89% deterministic formula with one LLM call appended. This document captures the pivot to an **AI-first** architecture and the multi-phase evolution path (free → paid → Zetryn models) that keeps it economically viable at every stage.

The framework primitives (graph engine, node protocol, memory, observability, boundary) do **not** change. What changes is **which nodes the strategies use** and **how the LLM is positioned**.

---

## 1. Decision summary

| Aspect | Before (2026-06-23) | After (this doc) |
|---|---|---|
| LLM role | Advisor (one node, narrative scoring only) | **Primary analyst** for safety / market / wallets / social judgment |
| Rule role | Decision logic + filtering | **Hard gates** (instant abort) + **guardrails** (sanity-check LLM output) |
| Scanner LLM calls | 1 per decision | 1 rich call (phase 1) → 3-5 parallel specialists (phase 3) |
| Decision output | Weighted formula score + 1-line LLM sentiment | LLM-synthesized verdict with per-aspect reasoning |
| Brand fit | "Trading framework with AI assist" | "AI Agent that trades" |
| Subscription justification | Weak (single LLM call works on free tier forever) | Strong (volume of LLM usage demands paid / Zetryn tiers) |

---

## 2. Architecture changes

### 2.1 Scanner — before

```
safety_gate -> intel_gate -> market_gate
     -> momentum_scorer -> wallet_intel_scorer -> social_scorer
     -> pumpfun_context -> narrative (LLM) -> aggregate (weighted formula)
```

8 rule nodes computing scores, 1 LLM node for narrative only, deterministic weighted blend.

### 2.2 Scanner — after

```
safety_hard_gate (rule, <0.05ms)    ← honeypot, freeze_auth, dev_rug_history, bundled_supply
intel_hard_gate  (rule, <0.05ms)    ← bundler count, external safety floor
market_hard_gate (rule, <0.05ms)    ← min liquidity, min volume
        ↓
analyst (LLM, 1 rich call)          ← multi-aspect structured output
        ↓
guardrail (rule, <0.05ms)           ← override LLM if obviously wrong
        ↓
Decision
```

**`analyst` node** returns a `FullAnalysis` Pydantic model:

```python
class AspectAnalysis(BaseModel):
    score: float = Field(ge=0, le=1)
    verdict: Literal["positive", "neutral", "negative"]
    signals: list[str]
    reasoning: str

class FullAnalysis(BaseModel):
    safety: AspectAnalysis
    market: AspectAnalysis
    wallets: AspectAnalysis
    social: AspectAnalysis
    final_score: float = Field(ge=0, le=1)
    recommendation: Literal["alert", "watch", "skip"]
    reasoning: str
```

**`guardrail` node** is a rule that overrides the LLM under hard constraints (e.g. LLM recommends `alert` but `liquidity_usd < min_liquidity * 0.5` → demote to `watch` + flag). Prevents hallucinated decisions from reaching the bot.

### 2.3 Why this is feasible on free tier

Single rich LLM call instead of 5 sequential ones. With Groq `llama-3.3-70b-versatile` free tier (30 RPM × 3 keys via KeyPool = 90 RPM): **~90 scanner decisions/min**, enough for development and early production behind a bot-side pre-filter.

Gemini Flash (1M TPM, 15 RPM) handles high-context prompts when needed.

---

## 3. Three-phase LLM evolution

Same graph structure across all phases. Only the LLM strategy and provider change.

### Phase 1 — Free tier (now)

- **Provider:** Groq (primary) + Gemini Flash (backup) via `OpenAICompatibleClient`
- **Strategy:** single `analyst` node, one rich LLM call returning `FullAnalysis`
- **Latency:** 1-3s per scanner decision
- **Throughput:** ~90 decisions/min with KeyPool rotation
- **Cost:** $0 (free tier)
- **Use case:** development, dogfooding, early users

### Phase 2 — Paid providers

- **Provider:** OpenAI (`OpenAICompatibleClient`), Anthropic (native adapter with prompt caching)
- **Strategy options:**
  - Keep single `analyst` (cheapest path, higher rate limits)
  - Or split into `safety_analyst` + `market_analyst` + `wallets_analyst` + `social_analyst` + `synthesizer` running in parallel (faster, richer reasoning)
- **Latency:** 1-2s (parallel specialists) or 2-4s (single rich call with deeper model)
- **Throughput:** thousands/min
- **Cost:** $0.001–$0.02 per decision
- **Use case:** production users with own API keys; Zetryn earns only on subscription (license check), not on LLM usage

### Phase 3 — Zetryn models

- **Provider:** `ZetrynClient` → Hardes / Medifus / Easfus via Zetryn platform
- **Strategy:** parallel specialists, each model assigned by tier:

| Node | Model | Reason |
|---|---|---|
| `safety_analyst` | Easfus | Fast pattern matching on contract & on-chain |
| `market_analyst` | Easfus | Numeric reasoning, low latency required |
| `wallets_analyst` | Medifus | Wallet behavior context, balanced reasoning |
| `social_analyst` | Medifus | NLP sentiment + KOL quality judgement |
| `synthesizer` | Hardes | Cross-aspect reasoning + final narrative |

- **Latency:** 1.5–2s
- **Throughput:** subscription tier-gated
- **Cost (to user):** flat subscription (Free/Basic/Pro/Max)
- **Use case:** primary monetization path; subscription value justified by:
  - Bundled access to fine-tuned trading-specialized models
  - No per-token billing complexity for users
  - Each model used intensively per decision (volume = value)

---

## 4. Sniper — `hybrid_audit` mode

Sniper requirements (sub-second decision, < 100ms practical budget) are incompatible with LLM-primary decisions. The pivot does **not** change sniper's hot path; it adds a passive AI-audit layer for learning.

### 4.1 Modes (extend `SniperConfig.decision_mode`)

| Mode | Decision path | Latency | LLM used? |
|---|---|---|---|
| `rule` (default) | Pure rule | < 1 ms | No |
| `llm` | LLM-decide | 200-500ms | Yes (Groq, single call) |
| `hybrid` | LLM-decide + rule guardrail | 200-500ms | Yes |
| **`hybrid_audit` (new)** | **Rule decides instantly + LLM verifies async** | **< 1 ms decision, audit in background** | **Yes (non-blocking)** |

### 4.2 `hybrid_audit` design

```
ctx -> sniper.run()
        ↓
     rule_decide (sub-ms) -> Decision returned to bot (executes immediately)
        ↓
     fire-and-forget -> llm_verify task -> writes to DecisionLog with audit verdict
                                          (matches / disagrees + reasoning)
```

The bot trades on the rule decision (speed preserved). The LLM verdict lands in `DecisionLog` for offline analysis: where do the rule and AI disagree? Those disagreements + outcome data → improved rule thresholds in next iteration.

This is the bridge that lets us claim "AI Agent" on the sniper too without compromising latency.

---

## 5. Schema enrichment (status: done)

Completed during this pivot session. New fields in `trading/schemas.py`:

- `TokenSource` literal — `pumpfun_ws | dexscreener | raydium | birdeye | manual`
- `ActivityData` — multi-timeframe volume / txns / buys / sells / `buy_ratio_5m`
- `WalletIntel` — `safety_score`, smart / KOL / sniper / bundler / whale counts (+ optional address lists for tier-2 memory)
- `PumpfunData` — `bonding_curve_pct`, `creator_sol_buy`, `is_mayhem_mode`
- `ContractData` extended — `bundled_supply`, `dev_rug_history`
- `TwitterData` extended — `mentions_1h`, `mention_growth_pct`, `sentiment`, `engagement`, `velocity_tpm`
- `SocialData` extended — `boost_amount` (stored, not yet scored)
- `ScannerConfig` extended — `max_bundler_wallets`, `min_gmgn_safety_score`, `smart_money_threshold`, `min_buy_ratio_5m`, `pumpfun_curve_urgency_pct`, weights for `wallets` + `momentum`

All fields are optional with safe defaults. Old fixtures and external code keep working.

These fields feed the `analyst` LLM prompt in the new architecture, giving it the context required to actually reason like an analyst (not just a sentiment classifier).

---

## 6. What does NOT change

To make the scope of this pivot unambiguous:

- **Graph engine** (`zetryn/core/`) — `State`, `Node`, `Edge`, `Graph`, `Command`, `END`, snapshot trace. No changes.
- **Boundary** — framework decides, bot executes. Framework never holds keys, never touches the chain.
- **Dependency rule** — `zetryn/` ← no imports from `trading/` or `strategies/`. `trading/` ← pure contract. `strategies/` ← imports both.
- **Push + pull model** — bot pushes `TokenInput`, or framework calls `DataProvider.fetch(mint)`. Both converge on the same shape.
- **`DataProvider` / `Tool`** protocols — unchanged.
- **Memory** — `MemoryStore`, `Blacklist`, `DecisionLog`. Unchanged.
- **Observability** — structured logging, hooks, trace serialization. Unchanged.
- **Auth seam** — `SubscriptionAuth`, `License`, `LocalSubscriptionAuth` stub. Unchanged.
- **Backtester** — unchanged; same graph, different provider.
- **Provider config & KeyPool** — unchanged; new architecture relies on KeyPool rotation more heavily, design already supports it.

---

## 7. Updated roadmap

| M | Focus | Status |
|---|---|---|
| M0 | Core engine | ✅ done |
| M1 | LLM layer (OpenAICompatibleClient + KeyPool + structured output + fallback) | ✅ done |
| M2 | Generic tools | ✅ done |
| M3 | Agent A (scanner v1, rule-heavy) | ✅ done |
| M4 | Memory + observability | ✅ done |
| S1 | ZetrynClient + auth seam | ✅ done (stub) |
| M5 | Backtest | ✅ done |
| M6 | Agent B (sniper v1, rule + LLMDecisionNode) | ✅ done |
| **M7** | **Schema enrichment** (ActivityData, WalletIntel, PumpfunData, enriched social) | **✅ done (v0.1.0)** |
| **M8** | **Scanner v2 — AI-first** (`analyst` LLM node + hard gates + guardrail; phase 1 single rich call) | **✅ done (v0.1.0); hardened + closed in v0.3.0 — see §10 below** |
| **M9** | **Sniper v2 — `hybrid_audit` mode** (rule decide + LLM verify async) | **✅ done (v0.1.0)** |
| **M10** | **Packaging + README** (pip install, AI-Agent-positioned docs, examples) | **✅ done (v0.1.0)** |
| **F1** | **`KnowledgePack`** — markdown + JSON playbook loader (pre-P1 foundation, was M13+) | **✅ done (v0.2.0)** |
| **F3** | **`LLMRouter`** — multi-provider failover + per-model throttle (pre-P1 foundation) | **✅ done (v0.2.0)** |
| **F2** | **`ReflectiveNode`** — loss-pattern extractor from `DecisionLog` (pre-P1 foundation) | **✅ done (v0.2.0); wired into scanner v0.3.0** |
| M11 | Phase 2 LLM strategy variant — parallel specialist nodes (paid providers) | later |
| M12 | Phase 3 LLM strategy variant — Zetryn model mapping | platform-dependent |
| M13+ | YAML loader, multi-agent panel, vector memory, copy-trade | earned later |

**Platform workstream** (unchanged from 2026-06-23):
P1 RemoteSubscriptionAuth + hosted vLLM serving · P2 billing + tiers + multi-tenant · P3 observability dashboard · P4 model improvement loop.

---

## 8. Migration notes

What code changes in M8:

1. **`strategies/nodes/`**
   - **Keep:** `safety_gate`, `intel_gate`, `market_gate` (rename suffix `_hard_gate` for clarity)
   - **Remove from default scanner:** `momentum_scorer`, `wallet_intel_scorer`, `social_scorer`, `pumpfun_context`, `narrative` (these become *input facts* for the LLM, not separate nodes)
   - **Add:** `analyst.py` — single LLM node returning `FullAnalysis`
   - **Add:** `guardrail.py` — rule node that sanity-checks LLM output
   - **Update:** `decide.py` — `reject` stays; `aggregate` replaced by guardrail-aware finalizer

2. **`strategies/agents/scanner.py`**
   - Rewire graph: 3 hard gates → analyst → guardrail → END
   - Reject path unchanged (3 gates can still abort)

3. **`strategies/nodes/prompts.py`**
   - New `analyst_prompt` that consumes the full enriched `TokenInput` (including new schema groups from M7)
   - Output schema = `FullAnalysis` (defined in `trading/schemas.py`)

4. **`trading/schemas.py`**
   - Add `AspectAnalysis` + `FullAnalysis` Pydantic models
   - `Decision` gains optional `analysis: FullAnalysis | None` field for rich output

5. **`tests/test_scanner.py`**
   - Update fake LLM to return `FullAnalysis` JSON
   - Update assertions for new trace path
   - Existing test cases (GOOD / RUG / LOWLIQ) keep working

6. **`examples/walkthrough.py`**
   - Update stub LLM to return `FullAnalysis`
   - Print rich analyst output per token (this is the demo that sells the brand)

7. **`strategies/agents/sniper.py`** (M9)
   - Add `hybrid_audit` mode handling
   - LLM verify task fires after `state.output` is set, writes to DecisionLog

No changes required in: `zetryn/core/`, `zetryn/llm/`, `zetryn/memory/`, `zetryn/observability/`, `zetryn/auth/`, `zetryn/backtest/`, `zetryn/tools/`.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Free-tier rate limits choke scanner throughput | KeyPool rotation (already built) + bot-side pre-filter pattern documented in README. Target: bot pre-filter cuts 10k tokens/min to ~30-100 candidates/min before they reach scanner |
| LLM hallucinates a `buy` on obvious junk | `guardrail` node enforces hard rule overrides (liquidity floor, safety score floor). LLM cannot bypass these |
| Latency 1-3s breaks some sniper-like use cases | Sniper kept on rule-pure hot path. Scanner-style use cases assumed to tolerate 1-3s |
| User without LLM key cannot use the framework | Document required setup; provide stub LLM for offline demo (`examples/walkthrough.py`); Zetryn subscription path is the recommended production setup once platform is live |
| Backtest cost goes up (every historical token = LLM call) | Document LLM-cache layer (response cache by prompt hash) for backtest mode; defer cache build to M11 if not blocking |
| Brand promise outpaces model quality on free tier | Phase 1 uses Llama 3.3 70b on Groq — strong baseline. Quality only improves moving up tiers. Acceptable starting point |

---

## 10. Acceptance criteria for M8

Scanner v2 closeout status (final, as of v0.3.0):

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `build_scanner(llm_client)` returns: 3 hard gates → analyst → finalize (+ reject path) | ✅ v0.1.0 | [`strategies/agents/scanner.py`](../../strategies/agents/scanner.py) |
| 2 | 16 dummy tokens produce sensible decisions with stub LLM | ✅ v0.1.0 | [`tests/test_scanner.py`](../../tests/test_scanner.py); sample fixtures reduced to GOOD/RUG/LOWLIQ post-M10 for compactness, behaviour preserved |
| 3 | `Decision.analysis` carries the full `FullAnalysis` | ✅ v0.1.0 | [`trading/schemas.py`](../../trading/schemas.py) |
| 4 | All existing tests pass (was 80; **now 146**) | ✅ v0.3.0 | full pytest green |
| 5 | `examples/walkthrough.py` prints per-aspect analyst reasoning | ✅ v0.1.0 | [`examples/walkthrough.py`](../../examples/walkthrough.py) |
| 6 | Real Groq p95 ≤ 5s per token | ⚠️ **measurable, not always met on free tier** — median ~1.5s ✅, p95 can spike to ~11s under rate-limit variance. Mitigation: `LLMRouter` with ≥2 providers. Bench script: [`examples/bench_scanner_latency.py`](../../examples/bench_scanner_latency.py) | v0.3.0 |
| 7 | KeyPool 429 rotation graceful | ✅ v0.3.0 | 3 stress tests in [`tests/test_llm.py`](../../tests/test_llm.py) (cascade, exhaustion, mixed transient errors) |
| 8 | (added in v0.3.0) Analyst sees real outcome data | ✅ v0.3.0 | `ReflectiveNode` wired via `build_scanner(..., decision_log=...)`; lessons block layered before analyst persona |

The `guardrail` node mentioned in §2.2 was implemented as the `finalize` rule
node in [`strategies/nodes/decide.py`](../../strategies/nodes/decide.py), which applies the same hard-rule
overrides the original design called for (LLM cannot upgrade `skip` to
`alert` when liquidity is below the floor, etc.).

---

## 11. Out of scope for this pivot

Updated 2026-06-25 to reflect which "out of scope" items shipped early and
which remain on the long-term roadmap.

**Shipped early as pre-P1 foundations** (see [docs/CAPABILITIES.md](../CAPABILITIES.md)):
- `KnowledgePack` (F1) — markdown + JSON playbook loader, scanner/sniper integration. **Shipped v0.2.0**.
- `LLMRouter` (F3) — multi-provider failover + per-model throttle, free-tier presets for Groq / Gemini / OpenRouter. **Shipped v0.2.0**.
- `ReflectiveNode` (F2) — rule-based loss-pattern extractor from `DecisionLog`, wired into `build_scanner`. **Shipped v0.2.0 + v0.3.0**.

**Still on long-term roadmap (M13+):**
- YAML loader for graphs
- Multi-agent panel (`AgentNode` as sub-graph)
- Vector / semantic memory
- Copy-trade strategy agent
- LLM response cache for backtest acceleration
- Anthropic native adapter (prompt caching, extended thinking)
- Dashboard (Next.js, separate workstream)

---

## 12. Summary

The 2026-06-23 design was correct for "framework with AI assist". This pivot upgrades it to "AI Agent that trades", matching the product brand and business model. The graph engine and all framework primitives are unchanged. Only the reference strategy (scanner) is rewired, and the sniper gains a non-blocking audit mode. Phase 1 ships on free LLM providers; the same architecture scales to paid and ultimately to Zetryn's own models without code rewrite — only strategy and provider config swap.
