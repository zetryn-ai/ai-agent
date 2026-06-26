# Graph Report - .  (2026-06-26)

## Corpus Check
- 96 files · ~58,911 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1535 nodes · 5044 edges · 71 communities (61 shown, 10 thin omitted)
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 1417 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_LLM Key Pool & Config|LLM Key Pool & Config]]
- [[_COMMUNITY_LLM Client & Guardrails|LLM Client & Guardrails]]
- [[_COMMUNITY_KOL Copy-Trade Example|KOL Copy-Trade Example]]
- [[_COMMUNITY_KOL Audit Mode Tests|KOL Audit Mode Tests]]
- [[_COMMUNITY_Rate Limit & LLM Router|Rate Limit & LLM Router]]
- [[_COMMUNITY_Knowledge Pack System|Knowledge Pack System]]
- [[_COMMUNITY_KOL Strategy Agent|KOL Strategy Agent]]
- [[_COMMUNITY_Backtester & Runner|Backtester & Runner]]
- [[_COMMUNITY_Core Graph & Edges|Core Graph & Edges]]
- [[_COMMUNITY_State Machine & Memory|State Machine & Memory]]
- [[_COMMUNITY_Examples & Shared Types|Examples & Shared Types]]
- [[_COMMUNITY_Scanner Agent & Analyst|Scanner Agent & Analyst]]
- [[_COMMUNITY_Analyst Prompt Engine|Analyst Prompt Engine]]
- [[_COMMUNITY_Auth & Subscription|Auth & Subscription]]
- [[_COMMUNITY_Router Tier & Tests|Router Tier & Tests]]
- [[_COMMUNITY_Capabilities & Docs|Capabilities & Docs]]
- [[_COMMUNITY_Agent Registry & Graph|Agent Registry & Graph]]
- [[_COMMUNITY_KOL Nodes & Fast Market|KOL Nodes & Fast Market]]
- [[_COMMUNITY_Sniper Agent|Sniper Agent]]
- [[_COMMUNITY_Tool Use Node & Tests|Tool Use Node & Tests]]
- [[_COMMUNITY_KOL Confirmed Mode Tests|KOL Confirmed Mode Tests]]
- [[_COMMUNITY_Decision Log & Reflection|Decision Log & Reflection]]
- [[_COMMUNITY_Sniper Nodes & Decisions|Sniper Nodes & Decisions]]
- [[_COMMUNITY_KOL Reflective Loop Tests|KOL Reflective Loop Tests]]
- [[_COMMUNITY_LLM Router & Entry Tests|LLM Router & Entry Tests]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]

## God Nodes (most connected - your core abstractions)
1. `LLMResult` - 212 edges
2. `Message` - 209 edges
3. `State` - 155 edges
4. `LLMError` - 139 edges
5. `ContractData` - 89 edges
6. `MarketData` - 88 edges
7. `HolderData` - 88 edges
8. `WalletIntel` - 85 edges
9. `LLMClient` - 68 edges
10. `build_kol_copytrade()` - 62 edges

## Surprising Connections (you probably didn't know these)
- `KnowledgePack` --semantically_similar_to--> `Knowledge Injection at Startup`  [INFERRED] [semantically similar]
  README.md → docs/CAPABILITIES.md
- `LLMRouter` --semantically_similar_to--> `Per-Model Throttle and Auto-Fallback`  [INFERRED] [semantically similar]
  README.md → docs/CAPABILITIES.md
- `ReflectiveNode` --semantically_similar_to--> `Reflective Analysis of Past Decisions`  [INFERRED] [semantically similar]
  README.md → docs/CAPABILITIES.md
- `LLMClient` --uses--> `LLMClient`  [INFERRED]
  examples/bench_scanner_latency.py → zetryn/llm/client.py
- `int` --uses--> `LLMClient`  [INFERRED]
  examples/bench_scanner_latency.py → zetryn/llm/client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Closed Learning Loop Pipeline** — readme_decision_log, readme_reflective_node, readme_knowledge_pack, readme_build_scanner [EXTRACTED 0.95]
- **Scanner Hard-Gate Filtering Pipeline** — readme_safety_gate, readme_intel_gate, readme_market_gate, readme_guardrail [EXTRACTED 1.00]
- **LLM Failover and Throttle Stack** — readme_llm_router, capabilities_router_entry, readme_key_pool, capabilities_rate_limit [EXTRACTED 1.00]

## Communities (71 total, 10 thin omitted)

### Community 0 - "LLM Key Pool & Config"
Cohesion: 0.07
Nodes (55): ProviderConfig, Provider configuration.  Config stores only the *names* of environment variables, Describes one OpenAI-compatible provider., Resolve keys. Literal ``keys`` win (testing); else read ``key_envs`` from env., KeyPool, Mandatory API-key pool with rotation.  Free-tier providers rate-limit aggressive, Round-robin pool of API keys with per-key cooldown on rate limit., LLMNode (+47 more)

### Community 1 - "LLM Client & Guardrails"
Cohesion: 0.10
Nodes (51): DecisionFallbackFn, GuardrailFn, LLMClient, The thin LLM client abstraction.  A single small interface lets nodes stay provi, Minimal completion interface.      ``tools`` accepts a list of OpenAI function-c, LLM layer: provider-agnostic advisor calls with structured output., LLMDecisionNode, LLMNode — an advisor step backed by an LLM with structured output.  Lives in the (+43 more)

### Community 2 - "KOL Copy-Trade Example"
Cohesion: 0.11
Nodes (52): BaseModel, _build_groq_client(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path (+44 more)

### Community 3 - "KOL Audit Mode Tests"
Cohesion: 0.12
Nodes (49): bool, Exception, float, KOLContext, LLMResult, Message, str, bool (+41 more)

### Community 4 - "Rate Limit & LLM Router"
Cohesion: 0.12
Nodes (39): RateLimit, Per-model limits. None means unlimited. Real numbers come from the platform., Multi-provider LLM router with per-model throttle enforcement.  `LLMRouter` wrap, Sliding-window counters for one router entry., Return True if a new request is allowed under current limits., Record a successful request with its token usage., One (provider, model) tuple inside a tier preset., _Throttle (+31 more)

### Community 5 - "Knowledge Pack System"
Cohesion: 0.06
Nodes (43): Static knowledge injection at agent build time.  A `KnowledgePack` loads markdow, KnowledgePack, KnowledgePackError, Filesystem-backed knowledge pack loader.  Layout (all keys optional — missing su, Raised when a pack cannot be loaded (missing dir, bad JSON, etc.)., An immutable bundle of static knowledge loaded from a directory.      Use `Knowl, One system message per markdown file, in filename order., All markdown blocks merged into a single system message.          Returns None i (+35 more)

### Community 6 - "KOL Strategy Agent"
Cohesion: 0.09
Nodes (44): build_kol_copytrade(), Build and compile the KOL copy-trade graph.      Args:         knowledge_pack: A, DecisionLog, Graph, int, KnowledgePack, KOLRegistry, LLMClient (+36 more)

### Community 7 - "Backtester & Runner"
Cohesion: 0.12
Nodes (36): Backtester, Runs a graph over a dataset and returns a :class:`BacktestResult`., main(), LLMResult, Message, Example: backtest the scanner over a small historical dataset.  Runs offline (st, _StubLLM, HistoricalCase (+28 more)

### Community 8 - "Core Graph & Edges"
Cohesion: 0.13
Nodes (33): Condition, Edge, Conditional transitions between nodes., A directed, optionally conditional transition.      The engine evaluates a node', GraphExecutionError, GraphValidationError, The graph engine: compile nodes + edges into a runnable agent.  Routing rule: if, Raised at compile time when the graph is structurally invalid. (+25 more)

### Community 9 - "State Machine & Memory"
Cohesion: 0.09
Nodes (34): Data flowing through the graph.      Attributes:         context: Input supplied, State, Emit, main(), Message, Example: scanner + observability (logging hooks) + memory (blacklist, decision l, _StubLLM, Observability: structured logging hooks + trace serialization. (+26 more)

### Community 10 - "Examples & Shared Types"
Cohesion: 0.06
Nodes (35): LLMResult, LLMResult, LLMResult, LLMResult, LLMResult, ToolRegistry, float, int (+27 more)

### Community 11 - "Scanner Agent & Analyst"
Cohesion: 0.11
Nodes (36): build_scanner(), Build and compile the AI-first scanner graph.      With an LLM client the flow i, neutral_analysis(), Conservative fallback when the LLM is unavailable.      Returns a skip recommend, DecisionLog, Graph, int, KnowledgePack (+28 more)

### Community 12 - "Analyst Prompt Engine"
Cohesion: 0.11
Nodes (29): analyst_prompt(), _lessons_block(), make_analyst_prompt(), AI analyst — the single LLM call that drives M8 scanner decisions.  Replaces the, Return a system message with the reflection summary, or None if absent., Return a prompt builder that prepends a knowledge pack + lessons block.      Lay, Message, State (+21 more)

### Community 13 - "Auth & Subscription"
Cohesion: 0.10
Nodes (26): Subscription auth seam that gates access to the Zetryn agent + models., Entitlement, License, LocalSubscriptionAuth, Subscription auth seam.  Gates access to the Zetryn agent + hosted models. The d, Lightweight, cached license validation — NOT per-run.      Validates once, cache, Result of verifying a subscription key., Verifies a subscription key and returns what it entitles. (+18 more)

### Community 14 - "Router Tier & Tests"
Cohesion: 0.08
Nodes (29): build_tier_entries(), get_free_tier_limit(), Look up a preset by provider + model. Returns None if unknown.      For OpenRout, Materialise a tier preset into a list of RouterEntry.      The caller is respons, test_get_free_tier_limit_exact_match(), test_get_free_tier_limit_openrouter_free_suffix(), test_get_free_tier_limit_unknown_returns_none(), _FakeClient (+21 more)

### Community 15 - "Capabilities & Docs"
Cohesion: 0.08
Nodes (34): Analyst System Prompt Layering, CAPABILITIES.md — Single Source of Truth, Knowledge Injection at Startup, KOLAnalystVerdict, ReflectionResult, Reflective Analysis of Past Decisions, Persisting Runtime Knowledge, Scanner Graph Shape with Reflect Node (+26 more)

### Community 16 - "Agent Registry & Graph"
Cohesion: 0.15
Nodes (28): Agent C — KOL Copy-Trade.  Consumes a `KOLContext` and emits a `Decision`. The b, Agent A — the memecoin scanner + scorer (M8 AI-first).  Flow (M8 pivot to AI-fir, Agent B — the auto-snipe agent.  Speed-first. Modes selected via ``SniperConfig., Graph, A directed graph of nodes that runs to produce a final ``State``., Deterministic step backed by a plain Python function.      The function mutates, RuleNode, Reference strategies built on the zetryn framework.  This is the proving ground: (+20 more)

### Community 17 - "KOL Nodes & Fast Market"
Cohesion: 0.17
Nodes (32): KOLBuyEvent, fast_market(), make_kol_quality(), Skip if liquidity/volume too thin, or bundler/sniper density too high., Factory: binds the bot's `KOLRegistry` to a rule node.      The node enforces, i, KOLRegistry, _ctx(), _event() (+24 more)

### Community 18 - "Sniper Agent"
Cohesion: 0.13
Nodes (27): build_sniper(), Build and compile the sniper graph.      If ``llm_client`` is None (or config ke, Graph, KnowledgePack, LLMClient, str, _ctx(), _FakeLLM (+19 more)

### Community 19 - "Tool Use Node & Tests"
Cohesion: 0.16
Nodes (27): Graph node that runs `tool_use_loop` and stores the result.      By default writ, ToolUseNode, ToolRegistry, Tests for the LLM tool-use loop and ToolUseNode., Tool errors do not crash the loop — they become a tool-role message., A model emitting malformed tool args is reported as tool failure, not crash., Model that never stops calling tools is bounded by max_iterations., Returns canned LLMResult objects in sequence, optionally raising. (+19 more)

### Community 20 - "KOL Confirmed Mode Tests"
Cohesion: 0.15
Nodes (27): _ctx(), _pack(), KnowledgePack, KOLContext, Path, K5 tests — KOL copy-trade `confirmed` mode (LLM analyst before sizing).  Uses sc, Analyst approves at multiplier=1.0 → final size = rule size., multiplier=0.5 cuts the rule size in half. (+19 more)

### Community 21 - "Decision Log & Reflection"
Cohesion: 0.13
Nodes (20): DecisionLog, _infer_feature_keys(), _is_numeric(), Pattern, _quartile_label(), Reflective node: read past decisions, extract loss patterns, inject lessons.  `R, Pick top-level keys that look like features (not run_id / action / outcome)., One observed loss pattern: a (feature, bucket) pair with stats. (+12 more)

### Community 22 - "Sniper Nodes & Decisions"
Cohesion: 0.18
Nodes (25): Decision, _audit_prompt(), fast_market(), fast_safety(), _latency_ms(), make_snipe_prompt(), Nodes for the auto-snipe agent.  Speed-first: pure-rule gates that can abort in, Return a snipe prompt builder that prepends a knowledge pack's blocks. (+17 more)

### Community 23 - "KOL Reflective Loop Tests"
Cohesion: 0.18
Nodes (23): _CapturingLLM, _ctx(), _pack(), DecisionLog, Path, K7 tests — KOL Copy-Trade x ReflectiveNode integration.  The reflective loop:, Write 3 KOL copy-trade losers with a common 'exit_pattern' feature     that the, Rule mode should accept (and ignore) decision_log without error. (+15 more)

### Community 24 - "LLM Router & Entry Tests"
Cohesion: 0.23
Nodes (20): One provider in the router's failover chain., RouterEntry, FakeClient, str, Tests for the multi-provider LLM router., Scriptable LLMClient for tests., _result(), test_all_throttled_raises_no_keys() (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.14
Nodes (12): KOLProfile, KOLRegistry, Any, bool, float, int, KnowledgePack, str (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (22): Pure function: derive loss patterns from a list of decision records., Graph node: load recent decisions and write a lessons block to scratch.      Wri, reflect(), ReflectiveNode, float, str, Tests for the ReflectiveNode and underlying `reflect()` extractor., _record() (+14 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (21): _abort(), fast_safety(), kol_analyst_prompt(), kol_audit_prompt(), _latency_ms(), Nodes for the KOL copy-trade strategy.  The rule nodes (`fast_safety`, `kol_qual, Build the analyst prompt for `confirmed` mode.      The token has already passed, Compute final size and emit the buy Decision (terminal rule node).      Formula (+13 more)

### Community 28 - "Community 28"
Cohesion: 0.13
Nodes (21): KOLContext, _run(), Path, str, Tests for K1 (KOL schemas) and K2 (KOLRegistry from KnowledgePack)., _seed_pack(), test_kol_buy_event_rejects_negative_size(), test_kol_buy_event_required_fields() (+13 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (19): Message, Integration tests: ReflectiveNode wired into the scanner closes the learning loo, Reflect must not waste a memory read on tokens rejected by hard gates., Layering order: pack blocks first, then lessons, then analyst persona., reflect_window caps how many past records are summarised., Without an LLM, the reflect node makes no sense — it must not be added., Captures the messages the analyst sees so we can assert injection., Backwards-compat: an LLM-only build does not run the reflect node. (+11 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (13): test_registry_unknown_tool_is_graceful(), Tool, ToolResult, Generic tool machinery (chain-agnostic). Domain providers live in ``trading``., A registry of tools the caller injects for agent/LLM nodes to use., Holds named tools and runs them by name (safely)., ToolRegistry, Generic tool abstraction.  A tool is an open-ended capability an LLM/agent node (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.19
Nodes (9): _expired(), JSONFileStore, Simple cross-run persistence to a single JSON file.      Loads on init, writes o, test_json_file_store_persists(), Any, bool, float, Path (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.15
Nodes (17): Tests for the M2 generic tool system., test_registry_register_and_call(), test_registry_rejects_duplicate(), test_tool_graceful_on_exception(), test_tool_runs_async_fn(), test_tool_runs_sync_fn(), test_tool_timeout(), test_tool_validates_input_schema() (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (13): Blacklist, InMemoryStore, Zero-setup dict-backed store. Default for tests and ephemeral runs., Tests for the M4 memory layer., test_blacklist(), test_decision_log_and_stats(), test_inmemory_put_get_delete(), test_inmemory_ttl_expiry() (+5 more)

### Community 34 - "Community 34"
Cohesion: 0.18
Nodes (17): _build_llm(), _discover_keys(), _grep_float(), _grep_int(), _load_env_file(), main(), print_analysis(), print_input() (+9 more)

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (16): _build_provider(), _build_router_client(), _discover_keys(), _load_env_file(), main(), int, LLMClient, ProviderConfig (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (15): AnalystVerdict, check_rug(), CheckRugInput, get_smart_money_buys(), main(), int, Message, str (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.16
Nodes (10): A generic blacklist built on a MemoryStore.  Keys (token mints, dev wallets, any, A generic decision log built on a MemoryStore.  Stores one record per run (plain, Aggregate counts by action and PnL stats from recorded outcomes., Persistent memory: pluggable key-value store + blacklist + decision log., MemoryStore, Persistent memory: a small key-value interface with pluggable backends.  The fra, Namespaced key-value store., Any (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (18): _clamp(), intel_gate(), market_gate(), momentum_scorer(), pumpfun_context(), Deterministic rule nodes for the scanner.  Each reads the pushed ``TokenInput``, Score based on smart-money / KOL presence, penalised by sniper density., Compute pumpfun-specific flags. No-op for non-pumpfun tokens. (+10 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (12): Generic backtest harness: replay a graph over a historical dataset., BacktestResult, _get(), Generic backtest harness.  Runs a compiled graph over a dataset of (id, context), One backtested item: the decision produced and the known outcome (if any)., Domain-agnostic: count decisions by their ``action`` attribute/key., Read ``key`` from a pydantic model, dataclass, dict, or object., RunRecord (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.21
Nodes (15): _ctx(), _payload(), Integration tests: `LLMRouter` is a drop-in `LLMClient` for the scanner.  The sc, After a 429, the primary stays on cooldown for the next scan too., Pack injection works regardless of whether LLMClient is router or bare., An `LLMClient` that returns a fixed text — or raises a scripted error., Single-entry router behaves like a bare LLMClient., Primary rate-limits → router transparently uses secondary. (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (15): _build_clients_by_provider(), _discover_keys(), _healthy_token(), _load_env_file(), main(), Path, str, KOL Copy-Trade with TIER_SPEED / TIER_QUALITY / TIER_VOLUME router presets.  v0. (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (13): _build_router(), _discover_keys(), _load_env_file(), main(), int, LLMResult, LLMRouter, Message (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (8): Anything the engine can execute as a sub-graph (duck-typed Graph)., Runnable, Protocol, RuleFn, Any, Command, State, str

### Community 44 - "Community 44"
Cohesion: 0.23
Nodes (12): _apply_guardrails(), finalize(), _latency_ms(), Reject and finalize nodes that produce the final ``Decision``.  In the M8 AI-fir, Produce a skip Decision when a hard gate fails. Names the failure., Return possibly-demoted analysis + list of guardrail messages.      Guardrails o, Convert the analyst's ``FullAnalysis`` into the final ``Decision``., reject() (+4 more)

### Community 45 - "Community 45"
Cohesion: 0.32
Nodes (11): _build_router(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path, str (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.24
Nodes (8): _EchoLLM, main(), Message, Path, Example: run the scanner with a deployment-specific KnowledgePack.  A `Knowledge, Stub LLM that echoes the system prompt it received via the reasoning field., Write a minimal pack: two markdown rules + a JSON blacklist., _seed_pack()

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (11): KOLAnalystVerdict, make_kol_audit_dispatch(), neutral_kol_verdict(), Conservative fallback when the analyst LLM is unavailable.      Defaults to appr, Background coroutine — call the LLM, parse to KOLAnalystVerdict.      Errors are, Build the audit-dispatch node for KOL copy-trade audit mode.      The decision i, _run_kol_audit(), Exception (+3 more)

### Community 48 - "Community 48"
Cohesion: 0.24
Nodes (5): Return the next available key, skipping those still cooling down., Put a key on cooldown after a rate-limit response., float, int, str

### Community 49 - "Community 49"
Cohesion: 0.31
Nodes (10): AuditVerdict, make_audit_dispatch(), Background coroutine: call LLM and return parsed AuditVerdict.      Errors are s, Build a node function that dispatches the audit task and returns immediately., _run_audit(), KnowledgePack, LLMClient, str (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (10): API Key Pool Rotation, Per-Model Throttle and Auto-Fallback, RateLimit (RPM/RPD/TPM/TPD), Reliability Pattern (LLMRouter Production Default), RouterEntry, Router Tier Presets (TIER_SPEED / TIER_QUALITY / TIER_VOLUME), KeyPool, LLMRouter (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.25
Nodes (5): _AuditLLM, bool, LLMResult, Message, Fake LLM that returns an AuditVerdict JSON.

### Community 53 - "Community 53"
Cohesion: 0.43
Nodes (4): main(), Message, Example: how a bot calls the zetryn scanner.  Runs fully offline with a stub LLM, _StubLLM

### Community 54 - "Community 54"
Cohesion: 0.38
Nodes (4): main(), Message, Example: the auto-snipe agent in pure-rule (fast) vs LLM/hybrid mode.  Shows the, _StubLLM

### Community 55 - "Community 55"
Cohesion: 0.40
Nodes (4): Return a deep copy of the current scratch for tracing., Apply a ``Command.update`` to scratch (shallow merge)., Any, str

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (3): Backtester, DataProvider, HistoricalDataProvider

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (3): State, TokenInput, TradingContext

## Knowledge Gaps
- **39 isolated node(s):** `LLMClient`, `str`, `KnowledgePack`, `Graph`, `float` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State Machine & Memory` to `LLM Key Pool & Config`, `LLM Client & Guardrails`, `KOL Copy-Trade Example`, `KOL Audit Mode Tests`, `Knowledge Pack System`, `KOL Strategy Agent`, `Core Graph & Edges`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Agent Registry & Graph`, `KOL Nodes & Fast Market`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `Decision Log & Reflection`, `Sniper Nodes & Decisions`, `KOL Reflective Loop Tests`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 34`, `Community 35`, `Community 36`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 42`, `Community 43`, `Community 44`, `Community 45`, `Community 46`, `Community 52`, `Community 53`, `Community 54`, `Community 55`?**
  _High betweenness centrality (0.277) - this node is a cross-community bridge._
- **Why does `LLMResult` connect `Examples & Shared Types` to `LLM Key Pool & Config`, `LLM Client & Guardrails`, `KOL Copy-Trade Example`, `KOL Audit Mode Tests`, `Rate Limit & LLM Router`, `KOL Strategy Agent`, `Backtester & Runner`, `State Machine & Memory`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `KOL Reflective Loop Tests`, `LLM Router & Entry Tests`, `Community 29`, `Community 34`, `Community 35`, `Community 36`, `Community 40`, `Community 42`, `Community 46`, `Community 51`, `Community 53`, `Community 54`?**
  _High betweenness centrality (0.177) - this node is a cross-community bridge._
- **Why does `Message` connect `LLM Client & Guardrails` to `LLM Key Pool & Config`, `KOL Copy-Trade Example`, `KOL Audit Mode Tests`, `Rate Limit & LLM Router`, `Knowledge Pack System`, `KOL Strategy Agent`, `Backtester & Runner`, `State Machine & Memory`, `Examples & Shared Types`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `KOL Reflective Loop Tests`, `LLM Router & Entry Tests`, `Community 29`, `Community 34`, `Community 35`, `Community 36`, `Community 40`, `Community 42`, `Community 46`, `Community 51`, `Community 53`, `Community 54`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 180 inferred relationships involving `LLMResult` (e.g. with `LLMResult` and `Message`) actually correct?**
  _`LLMResult` has 180 INFERRED edges - model-reasoned connections that need verification._
- **Are the 206 inferred relationships involving `Message` (e.g. with `DecisionFallbackFn` and `LLMResult`) actually correct?**
  _`Message` has 206 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `State` (e.g. with `Condition` and `Edge`) actually correct?**
  _`State` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `LLMError` (e.g. with `DecisionFallbackFn` and `GuardrailFn`) actually correct?**
  _`LLMError` has 102 INFERRED edges - model-reasoned connections that need verification._