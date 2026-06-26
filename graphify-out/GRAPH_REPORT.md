# Graph Report - ai-agent-trading  (2026-06-27)

## Corpus Check
- 98 files · ~60,692 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1586 nodes · 5067 edges · 82 communities (69 shown, 13 thin omitted)
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 1394 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b53289ab`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

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
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]

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
- `LLMClient` --uses--> `LLMClient`  [INFERRED]
  examples/bench_scanner_latency.py → zetryn/llm/client.py
- `int` --uses--> `LLMClient`  [INFERRED]
  examples/bench_scanner_latency.py → zetryn/llm/client.py
- `str` --uses--> `State`  [INFERRED]
  tests/test_reflective_node.py → zetryn/core/state.py
- `float` --uses--> `State`  [INFERRED]
  tests/test_reflective_node.py → zetryn/core/state.py
- `KOLAnalystVerdict` --uses--> `Decision`  [INFERRED]
  strategies/nodes/kol_nodes.py → trading/schemas.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Closed Learning Loop Pipeline** — readme_decision_log, readme_reflective_node, readme_knowledge_pack, readme_build_scanner [EXTRACTED 0.95]
- **Scanner Hard-Gate Filtering Pipeline** — readme_safety_gate, readme_intel_gate, readme_market_gate, readme_guardrail [EXTRACTED 1.00]
- **LLM Failover and Throttle Stack** — readme_llm_router, capabilities_router_entry, readme_key_pool, capabilities_rate_limit [EXTRACTED 1.00]

## Communities (82 total, 13 thin omitted)

### Community 0 - "LLM Key Pool & Config"
Cohesion: 0.06
Nodes (59): ProviderConfig, Provider configuration.  Config stores only the *names* of environment variables, Describes one OpenAI-compatible provider., Resolve keys. Literal ``keys`` win (testing); else read ``key_envs`` from env., KeyPool, Mandatory API-key pool with rotation.  Free-tier providers rate-limit aggressive, Round-robin pool of API keys with per-key cooldown on rate limit., OpenAICompatibleClient (+51 more)

### Community 1 - "LLM Client & Guardrails"
Cohesion: 0.11
Nodes (55): DecisionFallbackFn, GuardrailFn, LLMClient, The thin LLM client abstraction.  A single small interface lets nodes stay provi, Minimal completion interface.      ``tools`` accepts a list of OpenAI function-c, LLM layer: provider-agnostic advisor calls with structured output., LLMDecisionNode, LLMNode (+47 more)

### Community 2 - "KOL Copy-Trade Example"
Cohesion: 0.11
Nodes (60): BaseModel, _build_groq_client(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path (+52 more)

### Community 3 - "KOL Audit Mode Tests"
Cohesion: 0.12
Nodes (44): bool, Exception, float, LLMResult, Message, str, bool, Exception (+36 more)

### Community 4 - "Rate Limit & LLM Router"
Cohesion: 0.10
Nodes (39): RateLimit, Per-model limits. None means unlimited. Real numbers come from the platform., build_tier_entries(), LLMRouter, Multi-provider LLM router with per-model throttle enforcement.  `LLMRouter` wrap, Sliding-window counters for one router entry., Return True if a new request is allowed under current limits., Record a successful request with its token usage. (+31 more)

### Community 5 - "Knowledge Pack System"
Cohesion: 0.08
Nodes (31): Static knowledge injection at agent build time.  A `KnowledgePack` loads markdow, KnowledgePack, KnowledgePackError, Filesystem-backed knowledge pack loader.  Layout (all keys optional — missing su, Raised when a pack cannot be loaded (missing dir, bad JSON, etc.)., An immutable bundle of static knowledge loaded from a directory.      Use `Knowl, One system message per markdown file, in filename order., All markdown blocks merged into a single system message.          Returns None i (+23 more)

### Community 6 - "KOL Strategy Agent"
Cohesion: 0.11
Nodes (40): build_kol_copytrade(), Build and compile the KOL copy-trade graph.      Args:         knowledge_pack: A, DecisionLog, Graph, int, KnowledgePack, KOLRegistry, LLMClient (+32 more)

### Community 7 - "Backtester & Runner"
Cohesion: 0.15
Nodes (23): Backtester, Runs a graph over a dataset and returns a :class:`BacktestResult`., main(), LLMResult, Message, Example: backtest the scanner over a small historical dataset.  Runs offline (st, _StubLLM, HistoricalCase (+15 more)

### Community 8 - "Core Graph & Edges"
Cohesion: 0.13
Nodes (26): Condition, Edge, Conditional transitions between nodes., A directed, optionally conditional transition.      The engine evaluates a node', GraphExecutionError, GraphValidationError, The graph engine: compile nodes + edges into a runnable agent.  Routing rule: if, Raised at compile time when the graph is structurally invalid. (+18 more)

### Community 9 - "State Machine & Memory"
Cohesion: 0.17
Nodes (23): Hooks, Optional callbacks fired around each node. Sync or async are both fine., Data flowing through the graph.      Attributes:         context: Input supplied, State, Emit, _default_emit(), logging_hooks(), Structured logging hooks.  ``logging_hooks`` returns a :class:`Hooks` that emits (+15 more)

### Community 10 - "Examples & Shared Types"
Cohesion: 0.08
Nodes (29): _grep_float(), _grep_int(), float, int, LLMResult, Message, str, LLMResult (+21 more)

### Community 11 - "Scanner Agent & Analyst"
Cohesion: 0.13
Nodes (27): build_scanner(), Agent A — the memecoin scanner + scorer (M8 AI-first).  Flow (M8 pivot to AI-fir, Build and compile the AI-first scanner graph.      With an LLM client the flow i, DecisionLog, Graph, int, KnowledgePack, LLMClient (+19 more)

### Community 12 - "Analyst Prompt Engine"
Cohesion: 0.19
Nodes (18): _pack(), KnowledgePack, Path, str, Integration tests: KnowledgePack injection into scanner / sniper prompts., When no pack and no lessons are present, output equals analyst_prompt., An empty pack adds no blocks; output equals analyst_prompt., _SnipeLLM (+10 more)

### Community 13 - "Auth & Subscription"
Cohesion: 0.10
Nodes (26): Subscription auth seam that gates access to the Zetryn agent + models., Entitlement, License, LocalSubscriptionAuth, Subscription auth seam.  Gates access to the Zetryn agent + hosted models. The d, Lightweight, cached license validation — NOT per-run.      Validates once, cache, Result of verifying a subscription key., Verifies a subscription key and returns what it entitles. (+18 more)

### Community 14 - "Router Tier & Tests"
Cohesion: 0.07
Nodes (30): _build_router(), _discover_keys(), LLMRouter, str, Return (client, entry_names). client implements the LLMClient protocol., get_free_tier_limit(), Look up a preset by provider + model. Returns None if unknown.      For OpenRout, test_get_free_tier_limit_exact_match() (+22 more)

### Community 15 - "Capabilities & Docs"
Cohesion: 0.11
Nodes (24): Agent A — Scanner, Agent B — Sniper, AI-First Design Philosophy, build_scanner, Decision, DecisionLog, Strict Dependency Rule, FullAnalysis (+16 more)

### Community 16 - "Agent Registry & Graph"
Cohesion: 0.20
Nodes (25): Agent B — the auto-snipe agent.  Speed-first. Modes selected via ``SniperConfig., Graph, A directed graph of nodes that runs to produce a final ``State``., Deterministic step backed by a plain Python function.      The function mutates, RuleNode, test_backtester_collects_decisions_and_traces(), test_backtester_records_errors_and_continues(), build_linear() (+17 more)

### Community 17 - "KOL Nodes & Fast Market"
Cohesion: 0.16
Nodes (33): KOLBuyEvent, KOLRegistry, fast_market(), make_kol_quality(), Skip if liquidity/volume too thin, or bundler/sniper density too high., Factory: binds the bot's `KOLRegistry` to a rule node.      The node enforces, i, _ctx(), _event() (+25 more)

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
Cohesion: 0.09
Nodes (24): AgentNode, Node primitives.  A node is the unit of work. Every node exposes the same tiny i, Anything the engine can execute as a sub-graph (duck-typed Graph)., Extension point: a node whose work is another graph (sub-agent).      The sub-gr, Runnable, Command, Dynamic routing escape hatch returned by a node.      A node may return a ``Comm, _is_numeric() (+16 more)

### Community 22 - "Sniper Nodes & Decisions"
Cohesion: 0.20
Nodes (22): Decision, _audit_prompt(), fast_market(), fast_safety(), _latency_ms(), Nodes for the auto-snipe agent.  Speed-first: pure-rule gates that can abort in, Deterministic rails the LLM cannot breach (hybrid mode).      Forces abort on ru, Prompt asking the LLM whether it agrees with the rule-based snipe decision. (+14 more)

### Community 23 - "KOL Reflective Loop Tests"
Cohesion: 0.18
Nodes (23): _CapturingLLM, _ctx(), _pack(), DecisionLog, Path, K7 tests — KOL Copy-Trade x ReflectiveNode integration.  The reflective loop:, Write 3 KOL copy-trade losers with a common 'exit_pattern' feature     that the, Rule mode should accept (and ignore) decision_log without error. (+15 more)

### Community 24 - "LLM Router & Entry Tests"
Cohesion: 0.22
Nodes (19): FakeClient, str, Tests for the multi-provider LLM router., Scriptable LLMClient for tests., _result(), test_all_throttled_raises_no_keys(), test_preset_can_be_attached_to_entry(), test_router_aclose_propagates() (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (20): Agent C — KOL Copy-Trade.  Consumes a `KOLContext` and emits a `Decision`. The b, KOLProfile, Reference strategies built on the zetryn framework.  This is the proving ground:, KOLRegistry, Any, bool, float, int (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (23): _infer_feature_keys(), Pattern, Reflective node: read past decisions, extract loss patterns, inject lessons.  `R, Pure function: derive loss patterns from a list of decision records., Pick top-level keys that look like features (not run_id / action / outcome)., One observed loss pattern: a (feature, bucket) pair with stats., Output of a single reflection pass — what gets written to scratch., reflect() (+15 more)

### Community 27 - "Community 27"
Cohesion: 0.11
Nodes (29): bool, Command, float, KnowledgePack, KOLAnalystVerdict, LLMClient, Message, _abort() (+21 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (18): test_sizing_clamps_at_max_size(), Path, str, Tests for K1 (KOL schemas) and K2 (KOLRegistry from KnowledgePack)., _seed_pack(), test_kol_buy_event_rejects_negative_size(), test_kol_buy_event_required_fields(), test_kol_copytrade_config_defaults() (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (21): LLMResult, Message, str, Integration tests: ReflectiveNode wired into the scanner closes the learning loo, Reflect must not waste a memory read on tokens rejected by hard gates., Layering order: pack blocks first, then lessons, then analyst persona., reflect_window caps how many past records are summarised., Without an LLM, the reflect node makes no sense — it must not be added. (+13 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (13): test_registry_unknown_tool_is_graceful(), Tool, ToolResult, Generic tool machinery (chain-agnostic). Domain providers live in ``trading``., A registry of tools the caller injects for agent/LLM nodes to use., Holds named tools and runs them by name (safely)., ToolRegistry, Generic tool abstraction.  A tool is an open-ended capability an LLM/agent node (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (9): _expired(), JSONFileStore, Simple cross-run persistence to a single JSON file.      Loads on init, writes o, test_json_file_store_persists(), Any, bool, float, Path (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.15
Nodes (17): Tests for the M2 generic tool system., test_registry_register_and_call(), test_registry_rejects_duplicate(), test_tool_graceful_on_exception(), test_tool_runs_async_fn(), test_tool_runs_sync_fn(), test_tool_timeout(), test_tool_validates_input_schema() (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (11): Blacklist, A generic blacklist built on a MemoryStore.  Keys (token mints, dev wallets, any, A generic decision log built on a MemoryStore.  Stores one record per run (plain, Persistent memory: pluggable key-value store + blacklist + decision log., MemoryStore, Persistent memory: a small key-value interface with pluggable backends.  The fra, Namespaced key-value store., bool (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.23
Nodes (13): _build_llm(), _discover_keys(), _load_env_file(), main(), print_analysis(), print_input(), print_output(), print_processing() (+5 more)

### Community 35 - "Community 35"
Cohesion: 0.22
Nodes (13): _build_provider(), _build_router_client(), _discover_keys(), _load_env_file(), main(), int, LLMClient, ProviderConfig (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (17): AnalystVerdict, check_rug(), CheckRugInput, get_smart_money_buys(), main(), int, LLMResult, Message (+9 more)

### Community 37 - "Community 37"
Cohesion: 0.27
Nodes (6): DecisionLog, Aggregate counts by action and PnL stats from recorded outcomes., test_reflective_node_requires_positive_window(), Any, MemoryStore, str

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (18): _clamp(), intel_gate(), market_gate(), momentum_scorer(), pumpfun_context(), Deterministic rule nodes for the scanner.  Each reads the pushed ``TokenInput``, Score based on smart-money / KOL presence, penalised by sniper density., Compute pumpfun-specific flags. No-op for non-pumpfun tokens. (+10 more)

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (11): Generic backtest harness: replay a graph over a historical dataset., BacktestResult, _get(), One backtested item: the decision produced and the known outcome (if any)., Domain-agnostic: count decisions by their ``action`` attribute/key., Read ``key`` from a pydantic model, dataclass, dict, or object., RunRecord, MetricsFn (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.21
Nodes (15): _ctx(), _payload(), Integration tests: `LLMRouter` is a drop-in `LLMClient` for the scanner.  The sc, After a 429, the primary stays on cooldown for the next scan too., Pack injection works regardless of whether LLMClient is router or bare., An `LLMClient` that returns a fixed text — or raises a scripted error., Single-entry router behaves like a bare LLMClient., Primary rate-limits → router transparently uses secondary. (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.23
Nodes (13): _build_clients_by_provider(), _discover_keys(), _load_env_file(), main(), Path, KOL Copy-Trade with TIER_SPEED / TIER_QUALITY / TIER_VOLUME router presets.  v0., Build a client per provider, only for those with keys in env.      Returns a dic, _seed_pack() (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.24
Nodes (8): _load_env_file(), main(), int, LLMResult, Message, Example: scanner driven by `LLMRouter` with multi-provider failover.  This is th, Fallback when no provider keys are configured., _StubLLM

### Community 43 - "Community 43"
Cohesion: 0.04
Nodes (45): [0.10.0] — 2026-06-26, [0.11.0] — 2026-06-27, [0.1.0] — 2026-06-24, [0.2.0] — 2026-06-24, [0.3.0] — 2026-06-25, [0.4.0] — 2026-06-25, [0.5.0] — 2026-06-25, [0.6.0] — 2026-06-25 (+37 more)

### Community 44 - "Community 44"
Cohesion: 0.23
Nodes (12): _apply_guardrails(), finalize(), _latency_ms(), Reject and finalize nodes that produce the final ``Decision``.  In the M8 AI-fir, Produce a skip Decision when a hard gate fails. Names the failure., Return possibly-demoted analysis + list of guardrail messages.      Guardrails o, Convert the analyst's ``FullAnalysis`` into the final ``Decision``., reject() (+4 more)

### Community 45 - "Community 45"
Cohesion: 0.32
Nodes (11): _build_router(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path, str (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (9): _EchoLLM, main(), LLMResult, Message, Path, Example: run the scanner with a deployment-specific KnowledgePack.  A `Knowledge, Stub LLM that echoes the system prompt it received via the reasoning field., Write a minimal pack: two markdown rules + a JSON blacklist. (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (18): 1. Capability Matrix, 2. Gap Analysis (before P1–P4), 3. Foundation Work to Do Before P1, 4. Summary, 5. M8 closeout — Scanner v2 hardening, 6. Roadmap, ~~F1. `KnowledgePack` loader~~ — **Done (2026-06-24)**, ~~F2. `ReflectiveNode`~~ — **Done (2026-06-24)** (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.24
Nodes (5): Return the next available key, skipping those still cooling down., Put a key on cooldown after a rate-limit response., float, int, str

### Community 49 - "Community 49"
Cohesion: 0.24
Nodes (13): AuditVerdict, make_audit_dispatch(), make_snipe_prompt(), Return a snipe prompt builder that prepends a knowledge pack's blocks., Background coroutine: call LLM and return parsed AuditVerdict.      Errors are s, Build a node function that dispatches the audit task and returns immediately., _run_audit(), KnowledgePack (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (4): KeyPool, LLMRouter, OpenAICompatibleClient, ProviderConfig

### Community 51 - "Community 51"
Cohesion: 0.25
Nodes (5): _AuditLLM, bool, LLMResult, Message, Fake LLM that returns an AuditVerdict JSON.

### Community 53 - "Community 53"
Cohesion: 0.36
Nodes (5): main(), LLMResult, Message, Example: how a bot calls the zetryn scanner.  Runs fully offline with a stub LLM, _StubLLM

### Community 54 - "Community 54"
Cohesion: 0.32
Nodes (5): main(), LLMResult, Message, Example: the auto-snipe agent in pure-rule (fast) vs LLM/hybrid mode.  Shows the, _StubLLM

### Community 55 - "Community 55"
Cohesion: 0.40
Nodes (4): Return a deep copy of the current scratch for tracing., Apply a ``Command.update`` to scratch (shallow merge)., Any, str

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (3): Backtester, DataProvider, HistoricalDataProvider

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (3): State, TokenInput, TradingContext

### Community 59 - "Community 59"
Cohesion: 0.20
Nodes (17): system(), analyst_prompt(), _lessons_block(), make_analyst_prompt(), neutral_analysis(), AI analyst — the single LLM call that drives M8 scanner decisions.  Replaces the, Return a system message with the reflection summary, or None if absent., Return a prompt builder that prepends a knowledge pack + lessons block.      Lay (+9 more)

### Community 71 - "Community 71"
Cohesion: 0.19
Nodes (14): Graph node: load recent decisions and write a lessons block to scratch.      Wri, ReflectiveNode, InMemoryStore, Zero-setup dict-backed store. Default for tests and ephemeral runs., Tests for the M4 memory layer., test_blacklist(), test_decision_log_and_stats(), test_inmemory_put_get_delete() (+6 more)

### Community 72 - "Community 72"
Cohesion: 0.32
Nodes (13): RunRecord, ScannerConfig, _action(), build_items(), Any, str, TradingContext, Trading-specific backtest: historical dataset, outcomes, and metrics.  Pairs eac (+5 more)

### Community 73 - "Community 73"
Cohesion: 0.23
Nodes (10): Generic backtest harness.  Runs a compiled graph over a dataset of (id, context), Observability: structured logging hooks + trace serialization., Helpers to turn a run's trace into serializable data., Serialize the per-node trace (without the scratch snapshots, which may hold, A compact, loggable summary of a finished run., run_summary(), trace_to_dicts(), Any (+2 more)

### Community 74 - "Community 74"
Cohesion: 0.31
Nodes (10): NarrativeScore, narrative_prompt(), neutral_narrative(), Prompt builder + fallback for the narrative LLM advisor node.  Prompts are kept, Conservative fallback when the LLM is unavailable., Exception, Message, State (+2 more)

### Community 75 - "Community 75"
Cohesion: 0.25
Nodes (5): LLMResult, Message, Captures the messages sent to the LLM so we can assert injection., _RecordingLLM, test_scanner_without_pack_works_as_before()

### Community 76 - "Community 76"
Cohesion: 0.32
Nodes (5): main(), LLMResult, Message, Example: scanner + observability (logging hooks) + memory (blacklist, decision l, _StubLLM

### Community 77 - "Community 77"
Cohesion: 0.83
Nodes (3): _full_analysis_payload(), float, str

## Knowledge Gaps
- **86 isolated node(s):** `Fixed`, `Added`, `Notes`, `Added`, `Verified end-to-end` (+81 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State Machine & Memory` to `LLM Key Pool & Config`, `LLM Client & Guardrails`, `KOL Copy-Trade Example`, `KOL Audit Mode Tests`, `KOL Strategy Agent`, `Core Graph & Edges`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Agent Registry & Graph`, `KOL Nodes & Fast Market`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `Decision Log & Reflection`, `Sniper Nodes & Decisions`, `KOL Reflective Loop Tests`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 34`, `Community 35`, `Community 36`, `Community 38`, `Community 40`, `Community 41`, `Community 42`, `Community 44`, `Community 45`, `Community 46`, `Community 52`, `Community 53`, `Community 54`, `Community 55`, `Community 59`, `Community 71`, `Community 73`, `Community 74`, `Community 76`, `Community 79`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `LLMResult` connect `Examples & Shared Types` to `LLM Key Pool & Config`, `LLM Client & Guardrails`, `KOL Copy-Trade Example`, `KOL Audit Mode Tests`, `Rate Limit & LLM Router`, `KOL Strategy Agent`, `Backtester & Runner`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `KOL Reflective Loop Tests`, `LLM Router & Entry Tests`, `Community 29`, `Community 34`, `Community 36`, `Community 40`, `Community 42`, `Community 46`, `Community 51`, `Community 53`, `Community 54`, `Community 75`, `Community 76`, `Community 77`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Why does `Message` connect `LLM Client & Guardrails` to `LLM Key Pool & Config`, `KOL Copy-Trade Example`, `KOL Audit Mode Tests`, `Rate Limit & LLM Router`, `Knowledge Pack System`, `KOL Strategy Agent`, `Backtester & Runner`, `Examples & Shared Types`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `KOL Reflective Loop Tests`, `LLM Router & Entry Tests`, `Community 29`, `Community 34`, `Community 36`, `Community 40`, `Community 42`, `Community 46`, `Community 51`, `Community 53`, `Community 54`, `Community 59`, `Community 75`, `Community 76`, `Community 77`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 180 inferred relationships involving `LLMResult` (e.g. with `LLMResult` and `Message`) actually correct?**
  _`LLMResult` has 180 INFERRED edges - model-reasoned connections that need verification._
- **Are the 206 inferred relationships involving `Message` (e.g. with `DecisionFallbackFn` and `LLMResult`) actually correct?**
  _`Message` has 206 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `State` (e.g. with `Condition` and `Edge`) actually correct?**
  _`State` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `LLMError` (e.g. with `DecisionFallbackFn` and `GuardrailFn`) actually correct?**
  _`LLMError` has 102 INFERRED edges - model-reasoned connections that need verification._