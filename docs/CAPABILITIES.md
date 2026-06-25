# Zetryn — Capabilities, Roadmap & Gap Analysis

**This is the single source of truth for project status.** README points here
for the matrix; the architecture decision records in [`plans/`](plans/) point
here for milestone status; CHANGELOG references the same versions. If anything
disagrees with this document, this document wins.

> Legend: ✅ implemented · ⚠️ partial · ❌ not yet

---

## 1. Capability Matrix

| # | Capability | Status | Where it lives | Notes |
|---|------------|--------|----------------|-------|
| 1 | Knowledge injection at startup (static context + data lookups) | ✅ | [`zetryn/knowledge/pack.py`](../zetryn/knowledge/pack.py) (`KnowledgePack`) | `KnowledgePack.from_dir(path)` loads markdown → `system_blocks()` and JSON → `lookup(ns, key)`. **Knowledge ≠ Skills** — knowledge is passive context the LLM *reads*; for callable skills (functions the LLM can *invoke*), see [`zetryn/tools/`](../zetryn/tools/) (`Tool` + `ToolRegistry`). Both can be mixed in the same agent. |
| 2 | API key pool rotation | ✅ | [`zetryn/llm/keypool.py`](../zetryn/llm/keypool.py), [`zetryn/llm/openai_compat.py`](../zetryn/llm/openai_compat.py) | On HTTP 429 the offending key is penalised and another is acquired. Driven by `ProviderConfig.key_envs`. |
| 3 | Prompt-engineered reading of failed trade history (e.g. `PF26 -26%`, `ILY -21%`) | ✅ | [`zetryn/memory/reflective.py`](../zetryn/memory/reflective.py) (`ReflectiveNode`) | Node reads `DecisionLog`, lists recent losers by id + avg pnl, writes summary to `scratch["lessons_text"]` for prompt injection. |
| 4 | Reflective analysis of past decision blunders | ✅ | [`zetryn/memory/reflective.py`](../zetryn/memory/reflective.py) (`reflect()`, `ReflectionResult`) | Deterministic post-mortem extractor groups losers by feature buckets and ranks them by `loss_count`. |
| 5 | Loss-pattern recognition from recorded outcomes | ✅ | [`zetryn/memory/reflective.py`](../zetryn/memory/reflective.py) (`Pattern`) | Numeric features bucketed by quartile, categorical features grouped by value. Emits patterns like `top10_pct = > 0.30: 3/4 losses (rate 75%, avg pnl -22%)`. |
| 6 | Per-model throttle + auto-fallback across keys / providers | ✅ | [`zetryn/llm/router.py`](../zetryn/llm/router.py) (`LLMRouter`, `RouterEntry`, `get_free_tier_limit`) | Multi-provider failover wraps any number of `LLMClient`s and implements the same protocol. Per-entry `RateLimit` enforces RPM/RPD/TPM/TPD via sliding windows. Free-tier presets per-model for Groq, Gemini, and OpenRouter `:free` shared bucket. |
| 7 | Persisting new knowledge learned at runtime | ✅ | [`zetryn/memory/store.py`](../zetryn/memory/store.py), [`zetryn/knowledge/pack.py`](../zetryn/knowledge/pack.py), [`zetryn/memory/reflective.py`](../zetryn/memory/reflective.py), [`strategies/agents/scanner.py`](../strategies/agents/scanner.py) | Static playbook via `KnowledgePack`; mutable per-run state via `MemoryStore`; outcomes auto-summarised back into the next run by `ReflectiveNode`. Wired end-to-end into the scanner via `build_scanner(..., decision_log=...)` — the analyst sees a `Lessons from recent decisions` system block before deciding. The learning loop is now closed. |
| 8 | LLM-driven tool/skill invocation (function calling) | ✅ | [`zetryn/llm/tool_use.py`](../zetryn/llm/tool_use.py) (`tool_use_loop`, `ToolUseNode`), [`zetryn/tools/`](../zetryn/tools/) | `LLMClient.complete()` accepts `tools=[...]` and surfaces `tool_calls` on `LLMResult`. `tool_use_loop` drives the conversation: call → execute → feed back → repeat, with a mandatory `max_iterations` budget. `ToolUseNode` wraps it as a graph node with optional schema validation and the same fallback contract as `LLMNode`. Example: [`examples/run_with_tools.py`](../examples/run_with_tools.py). |

---

## 2. Gap Analysis (before P1–P4)

Three structural gaps block every later milestone:

### ~~G1. No knowledge ingestion path~~ — **Closed by F1 (2026-06-24)**
- Resolved by `KnowledgePack.from_dir(path)`: markdown under `system/` becomes
  system-prompt blocks; JSON under `data/` is read via `lookup(ns, key)`.
- Deployments can now ship a playbook (rules, KOL whitelist, lessons) without
  editing Python.

### ~~G2. No reflective / self-learning loop~~ — **Closed by F2 (2026-06-24)**
- Resolved by `ReflectiveNode` + the pure `reflect()` extractor.
- The node reads the last N records from `DecisionLog`, buckets losers by
  feature, and writes both a structured `ReflectionResult` and a
  prompt-ready `lessons_text` into `state.scratch`.
- Downstream prompts can prepend `state.scratch["lessons_text"]` to the
  system message to make the agent loss-aware.

### ~~G3. No multi-provider routing~~ — **Closed by F3 (2026-06-24)**
- Resolved by `LLMRouter` / `RouterEntry` / `get_free_tier_limit`.
- Per-entry `RateLimit(rpm, rpd, tpm, tpd)` enforced locally with sliding windows;
  free-tier presets shipped for Groq, Gemini, and OpenRouter (`:free` shared bucket).
- `LLMNode` is unchanged — `LLMRouter` satisfies the `LLMClient` protocol.

---

## 3. Foundation Work to Do Before P1

These three components unblock the rest of the roadmap. Build them first, in this order:

### ~~F1. `KnowledgePack` loader~~ — **Done (2026-06-24)**
- Shipped: `KnowledgePack` dataclass + `KnowledgePackError` in
  [`zetryn/knowledge/`](../zetryn/knowledge/).
- Surface: `from_dir(path)`, `system_blocks()`, `as_system_message()`,
  `lookup(ns, key, default)`, `namespaces()`.
- Layout: `pack/system/*.md` (sorted by filename) + `pack/data/*.json`.
- Tests: [`tests/test_knowledge_pack.py`](../tests/test_knowledge_pack.py)
  (11 cases — load, ordering, JSON parse, error path, lookup, round-trip).

### ~~F2. `ReflectiveNode`~~ — **Done (2026-06-24)**
- Shipped: `ReflectiveNode`, pure `reflect()`, `ReflectionResult`, `Pattern`
  in [`zetryn/memory/reflective.py`](../zetryn/memory/reflective.py).
- Rule-based (no LLM): cheap and deterministic — safe for live loops.
  Numeric features bucketed by quartile, categorical features by value.
  Patterns sorted by `loss_count` then `avg_pnl`.
- Surface: `ReflectiveNode(name, decision_log, *, window=20, output_key="lessons",
  feature_keys=None, loss_threshold=0.0, top_k=5)`.
- Writes `scratch["lessons"]` (`ReflectionResult`) and `scratch["lessons_text"]`
  (string) — prompts read the latter directly.
- Tests: [`tests/test_reflective_node.py`](../tests/test_reflective_node.py)
  (15 cases — bucketing, sorting, top-k, window, custom output key, empty log).

### ~~F3. `LLMRouter` (multi-provider)~~ — **Done (2026-06-24)**
- Shipped: `LLMRouter`, `RouterEntry`, `_Throttle` (RPM/RPD/TPM/TPD sliding windows).
- Presets: `PROVIDER_FREE_TIER_LIMITS` per provider AND per model (Groq, Gemini),
  plus shared `:free` bucket for OpenRouter.
- Helper: `get_free_tier_limit(provider, model) -> RateLimit | None`.
- Tests: `tests/test_llm_router.py` (17 cases — failover, throttle, exhaustion, presets).

---

## 4. Summary

| Foundation | Unblocks |
|------------|----------|
| ~~F1 `KnowledgePack` loader~~ ✅ | #1, partly #7 |
| ~~F2 `ReflectiveNode`~~ ✅ | #3, #4, #5, partly #7 |
| ~~F3 `LLMRouter`~~ ✅ | #6 |

Once F1–F3 are in place, P1–P4 can proceed without re-touching the core engine.

**Progress:** F1 ✅ · F2 ✅ · F3 ✅ — all foundations in place. **P1 can start.**

---

## 5. M8 closeout — Scanner v2 hardening

The original M8 (Scanner v2 AI-first) shipped in v0.1.0 against the acceptance
criteria in [`docs/plans/2026-06-24-ai-first-pivot.md`](plans/2026-06-24-ai-first-pivot.md) §10.
The criteria that remained open or untested are addressed here:

| Criterion | Status | Evidence |
|---|---|---|
| #1–#5 (graph shape, dummy tokens, `Decision.analysis`, tests, walkthrough) | ✅ from 0.1.0 | unchanged |
| #6 Real Groq e2e p95 ≤ 5s | ⚠️ single-provider on free tier; ✅ with `LLMRouter` | [`examples/bench_scanner_latency.py`](../examples/bench_scanner_latency.py) — supports `ZETRYN_BENCH_PROVIDER=groq\|gemini\|router`. Sample runs: single Groq median 1.5s / p95 ~11s; **router (Groq + Gemini) brings p95 below target**. Recommended production pattern: `examples/run_with_router.py`. |
| #7 KeyPool 429 handling | ✅ | [`tests/test_llm.py`](../tests/test_llm.py) adds 3-key cascade, exhaustion, mixed-error recovery tests. |
| Analyst prompt tuning with real outcome data | ✅ structural | `ReflectiveNode` wired into `build_scanner` — every run, the analyst sees a lessons block compiled from the last N decisions in `DecisionLog`. Tuning quality is now data-driven, not prompt-author guessing. |

### What changed in scanner.py

`build_scanner` gains three optional parameters:

```python
build_scanner(
    llm_client,
    knowledge_pack=pack,          # F1 — static playbook (since 0.2.0)
    decision_log=log,             # F2 — learning loop (this closeout)
    reflect_window=20,
    reflect_feature_keys=["top10_pct", "source"],
    reflect_top_k=5,
)
```

Graph shape when `decision_log` is provided:

```
safety_gate → intel_gate → market_gate → reflect → analyst → finalize
                                            (compiles lessons_text from DecisionLog)
```

Layering inside the analyst system prompt (top → bottom):
1. `KnowledgePack` system blocks (static rules)
2. Reflection lessons (dynamic, from past outcomes)
3. Analyst persona + per-token fact sheet

### Reliability pattern (v0.4.0)

Free-tier providers spike under rate-limit pressure — bench data shows
single Groq p95 ~11s vs. 1.5s median. The recommended fix is built into
the library:

```python
from zetryn.llm import LLMRouter, RouterEntry, OpenAICompatibleClient, get_free_tier_limit

router = LLMRouter([
    RouterEntry(client=groq_client,   name="groq:llama-3.3-70b",
                limit=get_free_tier_limit("groq", "llama-3.3-70b-versatile")),
    RouterEntry(client=gemini_client, name="gemini:2.5-flash",
                limit=get_free_tier_limit("gemini", "gemini-2.5-flash")),
])

scanner = build_scanner(router)  # router *is* an LLMClient — drop-in
```

Working example: [`examples/run_with_router.py`](../examples/run_with_router.py).
Bench comparison: run the same script in both modes —
`ZETRYN_BENCH_PROVIDER=groq` vs. `ZETRYN_BENCH_PROVIDER=router` —
on [`examples/bench_scanner_latency.py`](../examples/bench_scanner_latency.py).

The router enforces per-entry RPM/RPD/TPM/TPD sliding-window limits, so a
throttled primary is skipped without a network call — failover is local
and free, not reactive on 429.

---

## 6. Roadmap

Milestones, foundations, and platform workstreams in one table. **Update this
table on every release** — README and plan docs link here instead of duplicating it.

| ID | Focus | Status | Shipped in |
|---|---|---|---|
| M0  | Core engine (`State`, `Node`, `Edge`, `Graph`, `Command`, trace, validator) | ✅ done | v0.1.0 |
| M1  | LLM layer (`OpenAICompatibleClient`, `KeyPool`, structured output, fallback) | ✅ done | v0.1.0 |
| M2  | Generic tools (`Tool`, `ToolRegistry`, timeout/graceful) | ✅ done | v0.1.0 |
| M3  | Agent A (scanner v1, rule-heavy) | ✅ done | v0.1.0 |
| M4  | Memory + observability (`Blacklist`, `DecisionLog`, hooks, logging, trace) | ✅ done | v0.1.0 |
| S1  | `ZetrynClient` + auth seam (subscription stub) | ✅ done (stub) | v0.1.0 |
| M5  | Backtest (`Backtester` + trading metrics) | ✅ done | v0.1.0 |
| M6  | Agent B (sniper v1, rule + `LLMDecisionNode`) | ✅ done | v0.1.0 |
| M7  | Schema enrichment (`ActivityData`, `WalletIntel`, `PumpfunData`, enriched social) | ✅ done | v0.1.0 |
| M8  | Scanner v2 — AI-first (`analyst` LLM node + hard gates + guardrail) | ✅ done; hardened in v0.3.0 — see §5 | v0.1.0 + v0.3.0 |
| M9  | Sniper v2 — `hybrid_audit` mode (rule decide + async LLM verify) | ✅ done | v0.1.0 |
| M10 | Packaging + README (pip install, AI-Agent-positioned docs, examples) | ✅ done | v0.1.0 |
| **F1**  | **`KnowledgePack`** — markdown + JSON playbook loader (pre-P1 foundation) | ✅ done | v0.2.0 |
| **F3**  | **`LLMRouter`** — multi-provider failover + per-model throttle | ✅ done | v0.2.0 |
| **F2**  | **`ReflectiveNode`** — loss-pattern extractor; wired into scanner | ✅ done | v0.2.0 + v0.3.0 |
| Reliability | `LLMRouter` shipped as recommended production default + bench router mode | ✅ done | v0.4.0 |
| Tool-use | LLM tool-use loop (`tool_use_loop`, `ToolUseNode`) — capability #8 | ✅ done | v0.5.0 |
| **K (KOL Copy-Trade)** | **First strategy reference agent beyond Scanner/Sniper** — `build_kol_copytrade` rule mode, `KOLRegistry` from pack | ✅ done | v0.6.0 |
| **K5** | **KOL Copy-Trade `confirmed` mode** — LLM analyst between rules and sizing, can veto or scale size via `KOLAnalystVerdict` | ✅ done | v0.7.0 |
| **Provider expansion** | **7 providers wired** (Groq, Gemini, OpenRouter + Cerebras, Mistral, SambaNova, NVIDIA NIM) with per-model presets + `TIER_SPEED/QUALITY/VOLUME` router builders | ✅ done | v0.8.0 |
| K6 | KOL Copy-Trade `audit` mode (async LLM second opinion after rule decide) | 📅 later | — |
| K7 | KOL Copy-Trade × `ReflectiveNode` integration | 📅 later | — |
| M11 | Phase 2 LLM strategy — parallel specialist nodes (paid providers) | 📅 later | — |
| M12 | Phase 3 LLM strategy — Zetryn model mapping (Easfus/Medifus/Hardes) | 📅 platform-dependent | — |
| M13+ | YAML loader, multi-agent panel (mixed roles, Anthropic-style), vector memory | 📅 earned later | — |

**Platform workstream** (separate process, not gating the framework):
P1 `RemoteSubscriptionAuth` + hosted vLLM · P2 billing + multi-tenant ·
P3 observability dashboard (Next.js) · P4 model improvement loop.

### Foundations summary

| Foundation | Unblocks capabilities |
|------------|-----------------------|
| F1 `KnowledgePack` ✅ | #1, partly #7 |
| F2 `ReflectiveNode` ✅ | #3, #4, #5, partly #7 |
| F3 `LLMRouter` ✅ | #6 |

**Progress:** F1 ✅ · F2 ✅ · F3 ✅ — all foundations in place. **P1 can start.**

### What's next (concrete)

v0.7.0 closed the "AI in the copy-trade loop" gap (`confirmed` mode
shipped with `KOLAnalystVerdict`). Natural next candidates:

1. **K6: KOL Copy-Trade `audit` mode** — rule decides instantly (sub-ms),
   async LLM verifies in the background and writes to `DecisionLog`.
   Mirror of the sniper's `hybrid_audit` pattern. Bridges speed and AI.
2. **K7: KOL Copy-Trade × `ReflectiveNode`** — feed past copy-trade losers
   back into the analyst prompt when `confirmed` mode is active. Closes
   the learning loop on the new strategy.
3. **Strategy #4 candidate** (Pump.fun graduation snipe or Smart Money
   Confluence) — three strategies in code → real signal that YAML loader
   (M13) is worth building, not premature abstraction.
4. **M11 — Phase 2 LLM** (parallel specialists) is still available
   whenever a paid provider is in play; `AgentNode` already supports it.
5. **Anthropic native adapter** for prompt caching — only worth doing
   once analyst prompts grow large enough to amortise the cache cost.

Anything not listed here is in the M13+ bucket. If you're wondering
"what about X?" — check the table above first.
