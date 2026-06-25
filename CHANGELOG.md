# Changelog

All notable changes to `zetryn-trading` will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] — 2026-06-25

KOL Copy-Trade gains a real AI mode. Ships K5 of the milestone breakdown.
Triggered by a user observation in the v0.6.0 walkthrough run: with the
copy-trade strategy in rule-only mode, the "AI Agent" branding was thin
because no LLM ever ran in that flow. v0.7.0 closes that gap.

### Added
- **`KOLAnalystVerdict`** in `trading/schemas.py` — structured LLM
  output: `approve` (bool veto switch), `size_multiplier` in [0, 1.5]
  (scales the rule-derived size), `confidence`, `concerns` list,
  `reasoning`. Re-exported from `trading`.
- **`kol_analyst_prompt(state)`** + **`neutral_kol_verdict(state, exc)`**
  in `strategies/nodes/kol_nodes.py` — the analyst's job is *not* to
  re-decide the buy; it's to catch qualitative red flags the rules
  cannot encode and to nudge size based on confluence. Neutral
  fallback approves at multiplier=1.0 with `llm_failed=True` so an
  LLM outage never silently kills trades.
- **`mode="confirmed"`** in `build_kol_copytrade(...)` — opt-in flag
  that inserts the LLM analyst between `fast_market` and `sizing`.
  Requires `llm_client=...` (any `LLMClient`, including `LLMRouter`).
  Default mode stays `rule` — backwards compatible.
- **`sizing` node updated** to read `state.scratch["kol_analyst"]`:
  - `approve=False` → emits `action="skip"` with `analyst_veto=True`
  - `approve=True` → final size = rule_size × `size_multiplier`,
    still clamped at `max_size`
- **`examples/run_kol_copytrade.py`** updated with `ZETRYN_KOL_USE_GROQ=1`
  switch to demo the confirmed flow with real Groq.
- **10 new tests** in `tests/test_kol_confirmed_mode.py` covering
  approve / veto / size up / size down / LLM failure / garbage output /
  rule-mode backwards-compat / hard-gate short-circuit before LLM.
- **`docs/CAPABILITIES.md`** updated — K5 row marked done; §6 "What's
  next" reset to K6 (`audit` mode), K7 (Reflective integration), and a
  fourth-strategy candidate.

### Verified end-to-end
On real Groq Llama 3.3 70b with the example pack, the analyst
downgraded a rule-approved 2.47 SOL buy to 1.21 SOL (multiplier 0.5)
citing low_liquidity / no_social_presence / bundler_detected — proving
the LLM verdict materially shapes the final `Decision` rather than
being decorative.

### Changed
- **README §Status** — bumped to v0.7.0; "three reference strategies"
  section now mentions both KOL modes and links the env-var switch.

### Notes
- Boundary held: no fetcher landed inside the framework. The analyst
  sees the same `KOLContext` the bot already pushed; the bot still
  owns event subscription, KOL whitelist authoring, cooldown tracking,
  and trade execution.

## [0.6.0] — 2026-06-25

First strategy reference agent beyond Scanner/Sniper: **KOL Copy-Trade**
(`rule` mode). Ships K1-K4 of the milestone breakdown in
`docs/plans/2026-06-25-kol-copytrade-strategy.md`. `confirmed` (tool-use)
and `audit` modes follow in v0.7.0+; integration with `ReflectiveNode`
follows in v0.8.0.

### Added
- **Schemas** in `trading/schemas.py`: `KOLProfile`, `KOLBuyEvent`,
  `KOLCopyTradeConfig`, `KOLContext`. Re-exported from `trading`.
- **`strategies.KOLRegistry`** — typed read-only view over a
  `KnowledgePack`'s `data/kol_whitelist.json`. Exposes `get(wallet)`,
  `is_known(wallet)`, `passes_global_floor(profile)`, plus the
  pack-wide `min_tier` / `min_hit_rate`. Graceful when the pack has
  no whitelist (empty registry, not a crash).
- **`strategies/nodes/kol_nodes.py`** — pure-rule nodes:
  `fast_safety` (abort on dangerous contract), `make_kol_quality`
  (factory binding a `KOLRegistry`; enforces whitelist + pack floor +
  deployment-config floor + KOL min buy size + signal staleness +
  cooldown), `fast_market` (liquidity / volume / top10 / bundler /
  sniper gates), `sizing` (formula reads all tunables from
  `KOLCopyTradeConfig`).
- **`strategies.build_kol_copytrade(pack | registry=...)`** —
  compiled graph: `fast_safety → kol_quality → fast_market → sizing →
  END`. Re-exported from `strategies`.
- **Example** `examples/run_kol_copytrade.py` — six realistic scenarios
  (trusted KOL buy, unknown wallet, stale signal, honeypot override,
  cooldown, deployment override). Stub-only; no API key needed.
- **Tests**: `tests/test_kol_schemas_registry.py` (14 cases),
  `tests/test_kol_nodes.py` (19 cases), `tests/test_kol_copytrade.py`
  (10 cases). Suite is now 205 cases, all green.
- **Design doc**: `docs/plans/2026-06-25-kol-copytrade-strategy.md`
  captures the strategy hypothesis, boundary recap, schemas, graph,
  decisions §15, and phase breakdown §16.

### Changed
- **`README` §Status** — bumped to v0.6.0; reframed as "three reference
  agents" (Scanner / Sniper / KOL Copy-Trade) with example links.
- **`docs/CAPABILITIES.md` §6 Roadmap** — adds K (v0.6.0) row plus
  reliability and tool-use rows for v0.4.0 / v0.5.0; "What's next"
  reset to K5 (confirmed mode), K7 (reflective integration), and a
  fourth-strategy candidate as the natural next thread.

### Notes
- Boundary held tight: framework defines schemas, runs the decision
  graph, returns a `Decision`. The bot subscribes to KOL events,
  enriches `TokenInput`, maintains `kol_whitelist.json`, tracks
  cooldown state (`last_copy_ts`), and executes. No external data
  fetcher landed inside the framework.

## [0.5.0] — 2026-06-25

LLM tool-use loop shipped. Capability #8 in the matrix moves from ⚠️ to ✅:
the analyst can now invoke registered `Tool`s mid-decision using native
OpenAI-compatible function calling, with the same safety guarantees the rest
of the framework already enforces (bounded iterations, graceful tool failures,
fallback contract on total LLM failure).

### Added
- **`tool_use_loop()`** (`zetryn.llm.tool_use`) — drives the call → execute →
  feed-back → repeat conversation against any `LLMClient` and `ToolRegistry`.
  Returns the final `LLMResult` plus a `ToolUseTrace` (iterations, every tool
  call, truncation flag). `max_iterations` is mandatory and defaults to 6.
- **`ToolUseNode`** — graph node wrapping the loop. Optional `schema=...`
  parses the model's final text as Pydantic; with no schema it stores the raw
  text. Same fallback contract as `LLMNode`: on LLM/schema failure, applies
  `fallback_fn` and sets `<output_key>__llm_failed = True`.
- **`LLMResult.tool_calls`** — new field carrying the OpenAI-shaped tool call
  list when the model decides to invoke tools. Empty list when none requested.
- **`examples/run_with_tools.py`** — end-to-end demo: analyst sees a token,
  invokes `check_rug` and `get_smart_money_buys` on its own, returns a
  structured `AnalystVerdict`. Stub LLM so no API key needed.
- **`tests/test_tool_use.py`** — 11 cases covering the no-tools fast path,
  the call+continue loop, tool failures fed back to the model, malformed
  argument JSON, max-iteration truncation, schema parsing, and fallback paths.

### Changed
- **`LLMClient` protocol** — `complete()` accepts an optional `tools=[...]`
  keyword. Implementations that don't support tools may ignore it. Backwards
  compatible: existing fakes using `**kw` keep working; the one fake with an
  explicit signature in tests (`test_llm_router.py`) gained the parameter.
- **`OpenAICompatibleClient`** — forwards `tools` to the chat completions API,
  parses `message.tool_calls` from the response. Mutually exclusive with
  `json_mode` at the API level (matching OpenAI's contract).
- **`LLMRouter`** — forwards `tools` transparently to the active entry, so
  tool-use works through multi-provider failover with no extra wiring.
- **`docs/CAPABILITIES.md`** — capability #8 marked ✅ with evidence links;
  §6 "What's next" updated (both threads from v0.3.0 closed, new candidates
  identified).
- **`README` §Status** — bumped to v0.5.0 snapshot, lists the tool-use loop
  as built and points at the new example.

### Notes
- LLM tool-use is opt-in: existing scanner/sniper graphs don't change. To
  use it, instantiate a `ToolUseNode` with your `ToolRegistry` and add it to
  your graph in place of (or alongside) an `LLMNode`.

## [0.4.0] — 2026-06-25

Free-tier reliability pattern shipped as a working example and integration
tests. Closes M8 acceptance criterion #6 in practice: the scanner driven
by an `LLMRouter` with two free providers keeps p95 below the 5s target,
even when one provider rate-limits.

### Added
- **`examples/run_with_router.py`** — recommended production pattern:
  build `LLMRouter([groq, gemini])` with per-model free-tier presets and
  hand it straight to `build_scanner`. Falls back to a stub LLM when no
  keys are configured, so the demo always runs.
- **`examples/bench_scanner_latency.py` router mode** — new env knob
  `ZETRYN_BENCH_PROVIDER=router` benches the scanner through a
  multi-provider router so you can compare single-provider vs. router
  p95 directly. `ZETRYN_GROQ_MODEL` / `ZETRYN_GEMINI_MODEL` choose which
  model each entry uses.
- **`tests/test_scanner_router.py`** — 5 integration cases proving the
  router is a true drop-in `LLMClient`: single-entry equivalence,
  failover on `LLMRateLimitError`, graceful neutral verdict when every
  entry fails, persistent cooldown across scans, and `KnowledgePack`
  blocks reach the analyst through the router unchanged.

### Changed
- **`docs/CAPABILITIES.md` §5** — adds a "Reliability pattern" subsection
  with the recommended router snippet and a pointer to the bench script.
  Criterion #6 status is now "single-provider ⚠️ / router ✅".
- **README §Status** — clarifies that the router is the recommended
  production pattern, with a direct link to the new example.

### Notes
- No core API changed. `LLMRouter` already satisfied `LLMClient` since
  v0.2.0; v0.4.0 is the documentation + example + test layer proving it
  end-to-end inside the scanner.

## [0.3.0] — 2026-06-25

M8 closeout: the scanner's learning loop is now wired end-to-end. Past
losing decisions become a dynamic system-prompt block on every run, so
analyst output is conditioned on real outcomes — not just static prompt
authoring.

### Added
- **`build_scanner(..., decision_log=...)`** — when a `DecisionLog` is
  provided, a `ReflectiveNode` is inserted between the market hard gate
  and the analyst LLM. It compiles a `lessons_text` summary from the last
  N decisions (configurable via `reflect_window`, `reflect_feature_keys`,
  `reflect_top_k`) and the analyst sees it as a `Lessons from recent
  decisions` system block.
- **Analyst prompt layering** in `make_analyst_prompt(pack)` now stacks
  three layers top-to-bottom: `KnowledgePack` blocks → reflection lessons
  → analyst persona + per-token fact sheet.
- **`examples/bench_scanner_latency.py`** — latency benchmark for M8
  acceptance criterion #6. Validates real-provider p95 against the 5s
  target. Skips cleanly when no provider key is configured.
- **KeyPool stress tests** — three new cases in `tests/test_llm.py`:
  3-key cascade with mid-pool recovery, full-pool exhaustion,
  mixed 429+500+200 sequence with correct rotation accounting.
- **`tests/test_scanner_reflection.py`** — 7 cases covering scanner +
  reflective loop wiring, backwards compatibility, layering with
  KnowledgePack, and the no-LLM-no-reflect default path.

### Changed
- `make_analyst_prompt(None)` no longer returns `analyst_prompt` by
  identity — it returns a wrapper so the lessons block can be injected
  dynamically at run time. Behaviour-equivalent when no pack and no
  lessons are present; only test code using `is` identity needs updating.

### Notes
- M8 acceptance criterion #6 (p95 ≤ 5s) is now measurable with the bench
  script. Free-tier Groq frequently meets the median target (~1.5s) but
  p95 can spike past 5s under rate-limit variance. The recommended
  production mitigation is `LLMRouter` with ≥2 providers.

## [0.2.0] — 2026-06-24

Pre-P1 foundations: deployments can now ship their own playbook, fan out across
multiple LLM providers with per-model throttle, and re-use past trade outcomes
to make future decisions loss-aware.

### Added
- **`KnowledgePack`** (`zetryn.knowledge`) — markdown + JSON playbook loader.
  `KnowledgePack.from_dir(path)` reads `<pack>/system/*.md` as system-prompt
  blocks (filename order) and `<pack>/data/*.json` as structured lookups via
  `lookup(ns, key, default)`. Surfaces: `system_blocks()`,
  `as_system_message()`, `namespaces()`.
- **`LLMRouter`** (`zetryn.llm.router`) — multi-provider failover satisfying the
  `LLMClient` protocol; drops into existing `LLMNode` unchanged. Per-entry
  `RateLimit` enforced via sliding-window RPM/RPD/TPM/TPD counters.
  `PROVIDER_FREE_TIER_LIMITS` ships per-model presets for Groq (8 models),
  Gemini (5 models), and OpenRouter's `:free` shared bucket.
  `get_free_tier_limit(provider, model)` helper handles lookup safely.
- **`ReflectiveNode`** (`zetryn.memory.reflective`) — rule-based loss-pattern
  extractor over `DecisionLog`. Numeric features bucketed by quartile,
  categorical by value; writes `ReflectionResult` + ready-to-inject
  `lessons_text` to `state.scratch`. Pure `reflect()` helper exposed for direct
  use outside graphs.
- **Scanner + Sniper integration** — `build_scanner(..., knowledge_pack=pack)`
  and `build_sniper(..., knowledge_pack=pack)` prepend the pack's system blocks
  to the analyst, snipe-decide, and hybrid_audit prompts. Factories
  `make_analyst_prompt(pack)` and `make_snipe_prompt(pack)` exposed for custom
  graphs.
- **Example** `examples/run_with_knowledge.py` — runs the scanner with a
  throwaway pack, confirms house rules reach the LLM prompt.
- **`docs/CAPABILITIES.md`** — capability matrix and gap analysis, tracks
  F1–F3 foundation status.

### Changed
- `RateLimit` now has a `tpd` field (tokens-per-day), populated for Groq
  presets. Existing callers are unaffected — the default is `None`.
- README: architecture tree now lists `knowledge/`, `LLMRouter`, and
  `ReflectiveNode`; Phase 1 section mentions multi-provider failover; What's
  built includes the pre-P1 foundations row.

### Notes
- All three foundations are additive and backwards-compatible. Existing code
  paths (`build_scanner(llm)` without a pack, single-provider `OpenAICompatibleClient`)
  behave exactly as in 0.1.0.

## [0.1.0] — 2026-06-24

First public release. AI-first agent framework for Solana memecoin trading.

### Added
- **Core engine** (`zetryn.core`): `State`, `Node`, `Edge`, `Graph`, `Command`,
  `END` sentinel, per-node auto-snapshot trace, compile-time validation.
- **LLM layer** (`zetryn.llm`): `LLMClient` protocol, `OpenAICompatibleClient`
  (Groq / Gemini / OpenRouter / OpenAI), `KeyPool` rotation on 429, structured
  output with retry, `LLMNode`, `LLMDecisionNode`, `ZetrynClient` (subscription-
  gated, stub until platform live).
- **Tools** (`zetryn.tools`): `Tool` + `ToolRegistry`, graceful error handling.
- **Memory** (`zetryn.memory`): `MemoryStore` protocol, `InMemoryStore`,
  `JSONFileStore`, `Blacklist`, `DecisionLog`.
- **Observability** (`zetryn.observability`): structured per-node logging,
  `Hooks` protocol, trace serialization.
- **Auth seam** (`zetryn.auth`): `SubscriptionAuth`, `LocalSubscriptionAuth`,
  `License` with TTL cache and grace period, plan tiers (free/basic/pro/max).
- **Backtest** (`zetryn.backtest`): generic `Backtester` over `(id, context)`
  items with action distribution and pluggable metrics scorer.
- **Trading contract** (`trading/schemas.py`): `TokenInput`, `Decision`,
  `DataProvider` protocol, multi-timeframe `ActivityData`, `WalletIntel`,
  `PumpfunData`, enriched `SocialData` / `TwitterData`, `ContractData` with
  `bundled_supply` and `dev_rug_history`, `TokenSource` literal.
- **AI analyst schemas**: `AspectAnalysis`, `FullAnalysis`, `AuditVerdict`.
- **Reference strategies** (`strategies/`):
  - **Scanner (Agent A)** — AI-first: 3 hard gates (safety / intel / market) →
    1 rich LLM analyst → guardrail-aware finalize. Single LLM call returning
    structured multi-aspect verdict. Free-tier feasible.
  - **Sniper (Agent B)** — speed-first with 4 decision modes:
    `rule` (sub-ms pure-rule, default), `llm`, `hybrid` (LLM + rule guardrail),
    `hybrid_audit` (rule decides instantly, async LLM verify writes to
    DecisionLog — non-blocking hot path).
- **Examples**: `examples/walkthrough.py` (offline INPUT → PROCESSING → OUTPUT
  for 16 dummy memecoin scenarios), `examples/run_scanner.py`, `run_sniper.py`,
  `run_backtest.py`, `run_with_memory.py`.
- **Tests**: 80+ tests, no API key required (offline stubs + `MockDataProvider`).
- **Documentation**:
  - [`docs/plans/2026-06-23-zetryn-agent-framework-design.md`](docs/plans/2026-06-23-zetryn-agent-framework-design.md) — original design
  - [`docs/plans/2026-06-24-ai-first-pivot.md`](docs/plans/2026-06-24-ai-first-pivot.md) — AI-first pivot, 3-phase LLM evolution, sniper hybrid_audit
