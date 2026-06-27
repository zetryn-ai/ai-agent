# Graph Report - ai-agent  (2026-06-27)

## Corpus Check
- 114 files · ~73,752 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1945 nodes · 5921 edges · 95 communities (82 shown, 13 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 1513 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d142e989`
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
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]

## God Nodes (most connected - your core abstractions)
1. `LLMResult` - 212 edges
2. `Message` - 209 edges
3. `State` - 155 edges
4. `LLMError` - 139 edges
5. `State` - 98 edges
6. `ContractData` - 92 edges
7. `MarketData` - 91 edges
8. `HolderData` - 91 edges
9. `WalletIntel` - 85 edges
10. `LLMClient` - 68 edges

## Surprising Connections (you probably didn't know these)
- `DecisionLog` --uses--> `FullAnalysis`  [INFERRED]
  strategies/agents/scanner.py → trading/schemas.py
- `Graph` --uses--> `FullAnalysis`  [INFERRED]
  strategies/agents/scanner.py → trading/schemas.py
- `int` --uses--> `FullAnalysis`  [INFERRED]
  strategies/agents/scanner.py → trading/schemas.py
- `KnowledgePack` --uses--> `FullAnalysis`  [INFERRED]
  strategies/agents/scanner.py → trading/schemas.py
- `LLMClient` --uses--> `FullAnalysis`  [INFERRED]
  strategies/agents/scanner.py → trading/schemas.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Closed Learning Loop Pipeline** — readme_decision_log, readme_reflective_node, readme_knowledge_pack, readme_build_scanner [EXTRACTED 0.95]
- **Scanner Hard-Gate Filtering Pipeline** — readme_safety_gate, readme_intel_gate, readme_market_gate, readme_guardrail [EXTRACTED 1.00]
- **LLM Failover and Throttle Stack** — readme_llm_router, capabilities_router_entry, readme_key_pool, capabilities_rate_limit [EXTRACTED 1.00]

## Communities (95 total, 13 thin omitted)

### Community 0 - "LLM Key Pool & Config"
Cohesion: 0.07
Nodes (44): KeyPool, Round-robin pool of API keys with per-key cooldown on rate limit., Return the next available key, skipping those still cooling down., Put a key on cooldown after a rate-limit response., LLMNode, Calls an LLM advisor and stores a validated result into scratch., Return a validated instance of ``schema`` from the model., structured_complete() (+36 more)

### Community 1 - "LLM Client & Guardrails"
Cohesion: 0.08
Nodes (68): DecisionFallbackFn, LLMResult, Message, GuardrailFn, LLMClient, The thin LLM client abstraction.  A single small interface lets nodes stay provi, Minimal completion interface.      ``tools`` accepts a list of OpenAI function-c, LLMDecisionNode (+60 more)

### Community 2 - "KOL Copy-Trade Example"
Cohesion: 0.13
Nodes (48): BaseModel, _build_groq_client(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path (+40 more)

### Community 3 - "KOL Audit Mode Tests"
Cohesion: 0.13
Nodes (49): KOLBuyEvent, bool, Exception, float, KnowledgePack, KOLContext, LLMResult, Message (+41 more)

### Community 4 - "Rate Limit & LLM Router"
Cohesion: 0.12
Nodes (42): RateLimit, Per-model limits. None means unlimited. Real numbers come from the platform., build_tier_entries(), Multi-provider LLM router with per-model throttle enforcement.  `LLMRouter` wrap, Sliding-window counters for one router entry., Return True if a new request is allowed under current limits., Record a successful request with its token usage., One (provider, model) tuple inside a tier preset. (+34 more)

### Community 5 - "Knowledge Pack System"
Cohesion: 0.08
Nodes (31): Static knowledge injection at agent build time.  A `KnowledgePack` loads markdow, KnowledgePack, KnowledgePackError, Filesystem-backed knowledge pack loader.  Layout (all keys optional — missing su, Raised when a pack cannot be loaded (missing dir, bad JSON, etc.)., An immutable bundle of static knowledge loaded from a directory.      Use `Knowl, One system message per markdown file, in filename order., All markdown blocks merged into a single system message.          Returns None i (+23 more)

### Community 6 - "KOL Strategy Agent"
Cohesion: 0.12
Nodes (38): build_kol_copytrade(), Build and compile the KOL copy-trade graph.      Args:         knowledge_pack: A, DecisionLog, Graph, int, KnowledgePack, KOLRegistry, LLMClient (+30 more)

### Community 7 - "Backtester & Runner"
Cohesion: 0.11
Nodes (39): Backtester, Runs a graph over a dataset and returns a :class:`BacktestResult`., main(), LLMResult, Message, Example: backtest the scanner over a small historical dataset.  Runs offline (st, _StubLLM, main() (+31 more)

### Community 8 - "Core Graph & Edges"
Cohesion: 0.16
Nodes (21): Condition, Edge, Conditional transitions between nodes., A directed, optionally conditional transition.      The engine evaluates a node', GraphExecutionError, GraphValidationError, The graph engine: compile nodes + edges into a runnable agent.  Routing rule: if, Raised at compile time when the graph is structurally invalid. (+13 more)

### Community 9 - "State Machine & Memory"
Cohesion: 0.14
Nodes (24): Data flowing through the graph.      Attributes:         context: Input supplied, State, main(), Example: scanner + observability (logging hooks) + memory (blacklist, decision l, _StubLLM, Helpers to turn a run's trace into serializable data., Serialize the per-node trace (without the scratch snapshots, which may hold, A compact, loggable summary of a finished run. (+16 more)

### Community 10 - "Examples & Shared Types"
Cohesion: 0.11
Nodes (26): ProviderConfig, Provider configuration.  Config stores only the *names* of environment variables, Describes one OpenAI-compatible provider., Resolve keys. Literal ``keys`` win (testing); else read ``key_envs`` from env., LLM layer: provider-agnostic advisor calls with structured output., Mandatory API-key pool with rotation.  Free-tier providers rate-limit aggressive, OpenAICompatibleClient, OpenAI-compatible LLM client.  One adapter covers Groq, OpenRouter, and Gemini's (+18 more)

### Community 11 - "Scanner Agent & Analyst"
Cohesion: 0.18
Nodes (17): _ctx(), _FakeLLM, _full_analysis_payload(), float, str, TradingContext, M8 AI-first scanner end-to-end on sample TokenInput + fake LLM., If LLM hallucinates an alert with no liquidity, guardrail demotes to watch. (+9 more)

### Community 12 - "Analyst Prompt Engine"
Cohesion: 0.16
Nodes (21): make_analyst_prompt(), Return a prompt builder that prepends a knowledge pack + lessons block.      Lay, KnowledgePack, _pack(), KnowledgePack, Path, str, Integration tests: KnowledgePack injection into scanner / sniper prompts. (+13 more)

### Community 13 - "Auth & Subscription"
Cohesion: 0.10
Nodes (26): Subscription auth seam that gates access to the Zetryn agent + models., Entitlement, License, LocalSubscriptionAuth, Subscription auth seam.  Gates access to the Zetryn agent + hosted models. The d, Lightweight, cached license validation — NOT per-run.      Validates once, cache, Result of verifying a subscription key., Verifies a subscription key and returns what it entitles. (+18 more)

### Community 14 - "Router Tier & Tests"
Cohesion: 0.05
Nodes (48): _build_provider(), _build_router_client(), _discover_keys(), _load_env_file(), main(), int, LLMClient, ProviderConfig (+40 more)

### Community 15 - "Capabilities & Docs"
Cohesion: 0.11
Nodes (24): Agent A — Scanner, Agent B — Sniper, AI-First Design Philosophy, build_scanner, Decision, DecisionLog, Strict Dependency Rule, FullAnalysis (+16 more)

### Community 16 - "Agent Registry & Graph"
Cohesion: 0.18
Nodes (26): Agent C — KOL Copy-Trade.  Consumes a `KOLContext` and emits a `Decision`. The b, Agent B — the auto-snipe agent.  Speed-first. Modes selected via ``SniperConfig., Graph, A directed graph of nodes that runs to produce a final ``State``., Deterministic step backed by a plain Python function.      The function mutates, RuleNode, test_backtester_collects_decisions_and_traces(), test_backtester_records_errors_and_continues() (+18 more)

### Community 17 - "KOL Nodes & Fast Market"
Cohesion: 0.07
Nodes (60): bool, float, KnowledgePack, KOLAnalystVerdict, KOLRegistry, LLMClient, Message, _abort() (+52 more)

### Community 18 - "Sniper Agent"
Cohesion: 0.14
Nodes (25): build_sniper(), Build and compile the sniper graph.      If ``llm_client`` is None (or config ke, Graph, KnowledgePack, LLMClient, str, _ctx(), _FakeLLM (+17 more)

### Community 19 - "Tool Use Node & Tests"
Cohesion: 0.16
Nodes (25): ToolRegistry, Tests for the LLM tool-use loop and ToolUseNode., Tool errors do not crash the loop — they become a tool-role message., A model emitting malformed tool args is reported as tool failure, not crash., Model that never stops calling tools is bounded by max_iterations., Returns canned LLMResult objects in sequence, optionally raising., Realistic flow: model calls a tool, then emits a final JSON verdict., When the loop raises an LLMError, fallback_fn is applied. (+17 more)

### Community 20 - "KOL Confirmed Mode Tests"
Cohesion: 0.18
Nodes (24): _ctx(), _pack(), K5 tests — KOL copy-trade `confirmed` mode (LLM analyst before sizing).  Uses sc, Analyst approves at multiplier=1.0 → final size = rule size., multiplier=0.5 cuts the rule size in half., multiplier=1.5 boosts above rule size (still clamped at max_size)., approve=False → action becomes 'skip' even though rules approved., LLM error → neutral_kol_verdict fallback (approve True, mult 1.0). (+16 more)

### Community 21 - "Decision Log & Reflection"
Cohesion: 0.18
Nodes (8): Anything the engine can execute as a sub-graph (duck-typed Graph)., Runnable, Protocol, RuleFn, Any, Command, State, str

### Community 22 - "Sniper Nodes & Decisions"
Cohesion: 0.11
Nodes (40): Decision, GraduationVerdict, graduation_guardrail(), graduation_result(), _latency_ms(), Deterministic sizing → buy Decision (terminal rule node)., Deterministic rails the LLM cannot breach (hybrid mode)., rule_size_and_buy() (+32 more)

### Community 23 - "KOL Reflective Loop Tests"
Cohesion: 0.18
Nodes (23): _CapturingLLM, _ctx(), _pack(), DecisionLog, Path, K7 tests — KOL Copy-Trade x ReflectiveNode integration.  The reflective loop:, Write 3 KOL copy-trade losers with a common 'exit_pattern' feature     that the, Rule mode should accept (and ignore) decision_log without error. (+15 more)

### Community 24 - "LLM Router & Entry Tests"
Cohesion: 0.22
Nodes (19): One provider in the router's failover chain., RouterEntry, FakeClient, Tests for the multi-provider LLM router., Scriptable LLMClient for tests., _result(), test_all_throttled_raises_no_keys(), test_preset_can_be_attached_to_entry() (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (30): KOLProfile, KOLRegistry, Any, bool, float, int, KnowledgePack, str (+22 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (14): _infer_feature_keys(), _is_numeric(), Pattern, _quartile_label(), Reflective node: read past decisions, extract loss patterns, inject lessons.  `R, Pick top-level keys that look like features (not run_id / action / outcome)., One observed loss pattern: a (feature, bucket) pair with stats., Return a coarse bucket label for `v` based on the population `values`. (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.24
Nodes (17): _ctx(), _pack(), K4 end-to-end tests for build_kol_copytrade (rule mode)., Caller can pre-build a registry (e.g. assembled from multiple sources)., No whitelist → graph still compiles; runs reject with skip., test_below_deployment_min_hit_rate_skipped(), test_builder_accepts_empty_pack_gracefully(), test_cooldown_skips_repeat_copy() (+9 more)

### Community 28 - "Community 28"
Cohesion: 0.05
Nodes (70): build_graduation(), Agent D — Pump.fun graduation snipe (v0.12.0).  When a Pump.fun token graduates, Build and compile the graduation snipe graph.      Signature mirrors ``build_sni, _llm_client(), main(), _make_event(), GraduationEvent, LLMResult (+62 more)

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (27): build_scanner(), Build and compile the AI-first scanner graph.      With an LLM client the flow i, DecisionLog, Graph, int, KnowledgePack, LLMClient, str (+19 more)

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
Cohesion: 0.11
Nodes (18): Considered, NOT pursued (B/C-tier), KOL Copy-Trade (v0.6.0 → v0.11.0, K1–K7), MEV / Sandwich Bot — **C-tier**, Position Lifecycle Helpers, Pump.fun Graduation Snipe (v0.12.0), Roadmap strategies — A-tier, Roadmap strategies — S-tier (build next), Scanner (v0.1.0, hardened v0.3.0) (+10 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (20): _build_llm(), _discover_keys(), _grep_float(), _grep_int(), _load_env_file(), main(), print_analysis(), print_input() (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (36): LifecycleVerdict, _audit_prompt(), _decision(), emergency_exit(), _facts(), _hard_emit(), _hard_short_circuit_target(), hard_stop_loss() (+28 more)

### Community 36 - "Community 36"
Cohesion: 0.12
Nodes (17): AnalystVerdict, check_rug(), CheckRugInput, get_smart_money_buys(), main(), int, LLMResult, Message (+9 more)

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (25): _llm_client(), main(), LLMResult, Message, Example: position-lifecycle helpers (v0.13.0 / PL1).  Offline by default (stub L, _StubLLM, _CapturingLLM, _ctx() (+17 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (18): _clamp(), intel_gate(), market_gate(), momentum_scorer(), pumpfun_context(), Deterministic rule nodes for the scanner.  Each reads the pushed ``TokenInput``, Score based on smart-money / KOL presence, penalised by sniper density., Compute pumpfun-specific flags. No-op for non-pumpfun tokens. (+10 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (12): Generic backtest harness: replay a graph over a historical dataset., BacktestResult, _get(), Generic backtest harness.  Runs a compiled graph over a dataset of (id, context), One backtested item: the decision produced and the known outcome (if any)., Domain-agnostic: count decisions by their ``action`` attribute/key., Read ``key`` from a pydantic model, dataclass, dict, or object., RunRecord (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.19
Nodes (16): _ctx(), _payload(), str, Integration tests: `LLMRouter` is a drop-in `LLMClient` for the scanner.  The sc, After a 429, the primary stays on cooldown for the next scan too., Pack injection works regardless of whether LLMClient is router or bare., An `LLMClient` that returns a fixed text — or raises a scripted error., Single-entry router behaves like a bare LLMClient. (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (20): State, _AuditLLM, _ctx(), _FakeLLM, _pstate(), LLMResult, PositionContext, PositionState (+12 more)

### Community 42 - "Community 42"
Cohesion: 0.32
Nodes (11): _build_router(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path, str (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (10): [0.11.0] — 2026-06-27, [0.12.0] — 2026-06-27, [0.13.0] — 2026-06-27, Added, Added, Added, Design notes, Fixed (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (20): 0. Context, 1. What This Solves, 2. Framework Boundary, 3.1 `GraduationEvent`, 3.2 `GraduationConfig`, 3.3 `GraduationContext`, 3.4 `GraduationVerdict`, 3. Schema (`trading/schemas.py`) (+12 more)

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (32): build_lifecycle(), Agent E — Position Lifecycle Helpers (v0.13.0 / PL1).  First position-management, Build and compile the position-lifecycle graph.      Signature mirrors `build_sn, Graph, int, DecisionLog, KnowledgePack, LLMClient (+24 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (9): _EchoLLM, main(), LLMResult, Message, Path, Example: run the scanner with a deployment-specific KnowledgePack.  A `Knowledge, Stub LLM that echoes the system prompt it received via the reasoning field., Write a minimal pack: two markdown rules + a JSON blacklist. (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (18): 1. Capability Matrix, 2. Gap Analysis (before P1–P4), 3. Foundation Work to Do Before P1, 4. Summary, 5. M8 closeout — Scanner v2 hardening, 6. Roadmap, ~~F1. `KnowledgePack` loader~~ — **Done (2026-06-24)**, ~~F2. `ReflectiveNode`~~ — **Done (2026-06-24)** (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (17): Architecture, Auth seam (`zetryn/auth/`), Backtest (`zetryn/backtest/`), Commands, Commit identity (ROLLING RANDOM — no need to ask), Core engine (`zetryn/core/`), Dependency rules (strict), Documentation conventions (MUST FOLLOW) (+9 more)

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (21): Hooks, Engine lifecycle hooks.  Lightweight seam for observability: the engine fires th, Optional callbacks fired around each node. Sync or async are both fine., Invoke a hook callback, swallowing any error so it can't break the graph., safe_fire(), Immutable record of a single node execution., StepTrace, Emit (+13 more)

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (4): KeyPool, LLMRouter, OpenAICompatibleClient, ProviderConfig

### Community 51 - "Community 51"
Cohesion: 0.16
Nodes (27): AuditVerdict, Command, _abort(), _audit_prompt(), _grad_facts(), _grad_lessons_block(), graduation_gate(), graduation_prompt() (+19 more)

### Community 52 - "Community 52"
Cohesion: 0.08
Nodes (23): 0. Context, 1. What this solves, 2. Framework Boundary, 3.1 `PositionState`, 3.2 `LifecycleConfig`, 3.3 `PositionContext`, 3.4 `LifecycleVerdict` (LLM structured output for llm/hybrid), 3.5 `Decision` (extend existing) (+15 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (20): 0. Context, 1. What This Solves, 2. Framework Boundary, 3.1 `GraduationEvent`, 3.2 `GraduationConfig`, 3.3 `GraduationContext`, 3.4 `GraduationVerdict`, 3. Schema (`trading/schemas.py`) (+12 more)

### Community 54 - "Community 54"
Cohesion: 0.23
Nodes (12): _apply_guardrails(), finalize(), _latency_ms(), Reject and finalize nodes that produce the final ``Decision``.  In the M8 AI-fir, Produce a skip Decision when a hard gate fails. Names the failure., Return possibly-demoted analysis + list of guardrail messages.      Guardrails o, Convert the analyst's ``FullAnalysis`` into the final ``Decision``., reject() (+4 more)

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
Cohesion: 0.24
Nodes (8): _load_env_file(), main(), int, LLMResult, Message, Example: scanner driven by `LLMRouter` with multi-provider failover.  This is th, Fallback when no provider keys are configured., _StubLLM

### Community 71 - "Community 71"
Cohesion: 0.15
Nodes (12): Blacklist, A generic blacklist built on a MemoryStore.  Keys (token mints, dev wallets, any, A generic decision log built on a MemoryStore.  Stores one record per run (plain, Persistent memory: pluggable key-value store + blacklist + decision log., MemoryStore, Persistent memory: a small key-value interface with pluggable backends.  The fra, Namespaced key-value store., test_blacklist() (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.16
Nodes (20): Agent A — the memecoin scanner + scorer (M8 AI-first).  Flow (M8 pivot to AI-fir, system(), analyst_prompt(), _lessons_block(), neutral_analysis(), AI analyst — the single LLM call that drives M8 scanner decisions.  Replaces the, Return a system message with the reflection summary, or None if absent., Conservative fallback when the LLM is unavailable.      Returns a skip recommend (+12 more)

### Community 76 - "Community 76"
Cohesion: 0.22
Nodes (18): Pure function: derive loss patterns from a list of decision records., Output of a single reflection pass — what gets written to scratch., reflect(), ReflectionResult, float, str, Tests for the ReflectiveNode and underlying `reflect()` extractor., _record() (+10 more)

### Community 77 - "Community 77"
Cohesion: 0.19
Nodes (14): Graph node: load recent decisions and write a lessons block to scratch.      Wri, ReflectiveNode, InMemoryStore, Zero-setup dict-backed store. Default for tests and ephemeral runs., Tests for the M4 memory layer., test_decision_log_and_stats(), test_inmemory_put_get_delete(), test_inmemory_ttl_expiry() (+6 more)

### Community 78 - "Community 78"
Cohesion: 0.17
Nodes (17): _build_clients_by_provider(), _discover_keys(), _load_env_file(), main(), Path, KOL Copy-Trade with TIER_SPEED / TIER_QUALITY / TIER_VOLUME router presets.  v0., Build a client per provider, only for those with keys in env.      Returns a dic, _seed_pack() (+9 more)

### Community 79 - "Community 79"
Cohesion: 0.31
Nodes (10): NarrativeScore, narrative_prompt(), neutral_narrative(), Prompt builder + fallback for the narrative LLM advisor node.  Prompts are kept, Conservative fallback when the LLM is unavailable., Exception, Message, State (+2 more)

### Community 80 - "Community 80"
Cohesion: 0.23
Nodes (7): DecisionLog, Aggregate counts by action and PnL stats from recorded outcomes., Any, MemoryStore, str, Command, State

### Community 82 - "Community 82"
Cohesion: 0.20
Nodes (7): _AuditLLM, bool, LLMResult, Message, Fake LLM that returns an AuditVerdict JSON., Sniper decides via rule, dispatches background LLM audit, returns immediately., test_hybrid_audit_returns_rule_decision_instantly_and_dispatches_task()

### Community 83 - "Community 83"
Cohesion: 0.25
Nodes (5): LLMResult, Message, Captures the messages sent to the LLM so we can assert injection., _RecordingLLM, test_scanner_without_pack_works_as_before()

### Community 84 - "Community 84"
Cohesion: 0.25
Nodes (8): [0.5.0] — 2026-06-25, [0.6.0] — 2026-06-25, Added, Added, Changed, Changed, Notes, Notes

### Community 85 - "Community 85"
Cohesion: 0.32
Nodes (5): main(), LLMResult, Message, Example: the auto-snipe agent in pure-rule (fast) vs LLM/hybrid mode.  Shows the, _StubLLM

### Community 87 - "Community 87"
Cohesion: 0.40
Nodes (5): [0.7.0] — 2026-06-25, Added, Changed, Notes, Verified end-to-end

### Community 88 - "Community 88"
Cohesion: 0.40
Nodes (5): [0.9.0] — 2026-06-26, Added, Backwards compatibility, Notes, Verified end-to-end

### Community 89 - "Community 89"
Cohesion: 0.50
Nodes (3): [0.1.0] — 2026-06-24, Added, Changelog

### Community 90 - "Community 90"
Cohesion: 0.50
Nodes (4): [0.10.0] — 2026-06-26, Added, Notes, Verified end-to-end

### Community 91 - "Community 91"
Cohesion: 0.50
Nodes (4): [0.2.0] — 2026-06-24, Added, Changed, Notes

### Community 92 - "Community 92"
Cohesion: 0.50
Nodes (4): [0.3.0] — 2026-06-25, Added, Changed, Notes

### Community 93 - "Community 93"
Cohesion: 0.50
Nodes (4): [0.4.0] — 2026-06-25, Added, Changed, Notes

### Community 94 - "Community 94"
Cohesion: 0.50
Nodes (4): [0.8.0] — 2026-06-25, Added, Backwards compatibility, Notes

## Knowledge Gaps
- **185 isolated node(s):** `Documentation conventions (MUST FOLLOW)`, `Framework Boundary (NON-NEGOTIABLE — read first, every session)`, `Commit identity (ROLLING RANDOM — no need to ask)`, `Commands`, `Dependency rules (strict)` (+180 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State Machine & Memory` to `LLM Key Pool & Config`, `LLM Client & Guardrails`, `KOL Copy-Trade Example`, `KOL Strategy Agent`, `Backtester & Runner`, `Core Graph & Edges`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Agent Registry & Graph`, `KOL Nodes & Fast Market`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `Decision Log & Reflection`, `Sniper Nodes & Decisions`, `KOL Reflective Loop Tests`, `Community 26`, `Community 27`, `Community 29`, `Community 34`, `Community 36`, `Community 38`, `Community 39`, `Community 40`, `Community 42`, `Community 46`, `Community 49`, `Community 54`, `Community 55`, `Community 59`, `Community 72`, `Community 76`, `Community 77`, `Community 78`, `Community 79`, `Community 80`, `Community 82`, `Community 85`, `Community 86`?**
  _High betweenness centrality (0.149) - this node is a cross-community bridge._
- **Why does `LLMResult` connect `LLM Client & Guardrails` to `LLM Key Pool & Config`, `KOL Audit Mode Tests`, `Rate Limit & LLM Router`, `KOL Strategy Agent`, `Backtester & Runner`, `State Machine & Memory`, `Examples & Shared Types`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `KOL Reflective Loop Tests`, `LLM Router & Entry Tests`, `Community 29`, `Community 34`, `Community 36`, `Community 40`, `Community 46`, `Community 59`, `Community 72`, `Community 74`, `Community 82`, `Community 83`, `Community 85`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `State` connect `Community 41` to `Community 35`, `Community 37`, `Community 45`, `KOL Nodes & Fast Market`, `Community 51`, `Sniper Nodes & Decisions`, `Community 28`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 180 inferred relationships involving `LLMResult` (e.g. with `LLMResult` and `Message`) actually correct?**
  _`LLMResult` has 180 INFERRED edges - model-reasoned connections that need verification._
- **Are the 206 inferred relationships involving `Message` (e.g. with `DecisionFallbackFn` and `LLMResult`) actually correct?**
  _`Message` has 206 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `State` (e.g. with `Condition` and `Edge`) actually correct?**
  _`State` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `LLMError` (e.g. with `DecisionFallbackFn` and `GuardrailFn`) actually correct?**
  _`LLMError` has 102 INFERRED edges - model-reasoned connections that need verification._