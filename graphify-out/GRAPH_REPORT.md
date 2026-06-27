# Graph Report - ai-agent  (2026-06-27)

## Corpus Check
- 121 files · ~79,434 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2094 nodes · 6354 edges · 100 communities (87 shown, 13 thin omitted)
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 1590 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `134f6564`
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
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]

## God Nodes (most connected - your core abstractions)
1. `LLMResult` - 212 edges
2. `Message` - 209 edges
3. `State` - 155 edges
4. `LLMError` - 139 edges
5. `State` - 135 edges
6. `ContractData` - 92 edges
7. `MarketData` - 91 edges
8. `HolderData` - 91 edges
9. `WalletIntel` - 85 edges
10. `Decision` - 69 edges

## Surprising Connections (you probably didn't know these)
- `Any` --uses--> `KOLProfile`  [INFERRED]
  strategies/kol_registry.py → trading/schemas.py
- `int` --uses--> `KOLProfile`  [INFERRED]
  strategies/kol_registry.py → trading/schemas.py
- `KnowledgePack` --uses--> `KOLProfile`  [INFERRED]
  strategies/kol_registry.py → trading/schemas.py
- `DecisionLog` --uses--> `LifecycleVerdict`  [INFERRED]
  strategies/agents/lifecycle.py → trading/schemas.py
- `KnowledgePack` --uses--> `LifecycleVerdict`  [INFERRED]
  strategies/agents/lifecycle.py → trading/schemas.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Closed Learning Loop Pipeline** — readme_decision_log, readme_reflective_node, readme_knowledge_pack, readme_build_scanner [EXTRACTED 0.95]
- **Scanner Hard-Gate Filtering Pipeline** — readme_safety_gate, readme_intel_gate, readme_market_gate, readme_guardrail [EXTRACTED 1.00]
- **LLM Failover and Throttle Stack** — readme_llm_router, capabilities_router_entry, readme_key_pool, capabilities_rate_limit [EXTRACTED 1.00]

## Communities (100 total, 13 thin omitted)

### Community 0 - "LLM Key Pool & Config"
Cohesion: 0.24
Nodes (5): Return the next available key, skipping those still cooling down., Put a key on cooldown after a rate-limit response., float, int, str

### Community 1 - "LLM Client & Guardrails"
Cohesion: 0.10
Nodes (56): DecisionFallbackFn, GuardrailFn, LLMClient, The thin LLM client abstraction.  A single small interface lets nodes stay provi, Minimal completion interface.      ``tools`` accepts a list of OpenAI function-c, LLM layer: provider-agnostic advisor calls with structured output., LLMDecisionNode, LLMNode (+48 more)

### Community 2 - "KOL Copy-Trade Example"
Cohesion: 0.12
Nodes (50): BaseModel, _build_groq_client(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path (+42 more)

### Community 3 - "KOL Audit Mode Tests"
Cohesion: 0.13
Nodes (50): LLMClient, KOLBuyEvent, bool, Exception, float, KnowledgePack, KOLContext, LLMResult (+42 more)

### Community 4 - "Rate Limit & LLM Router"
Cohesion: 0.09
Nodes (53): RateLimit, Per-model limits. None means unlimited. Real numbers come from the platform., build_tier_entries(), LLMRouter, Multi-provider LLM router with per-model throttle enforcement.  `LLMRouter` wrap, Sliding-window counters for one router entry., Return True if a new request is allowed under current limits., Record a successful request with its token usage. (+45 more)

### Community 5 - "Knowledge Pack System"
Cohesion: 0.09
Nodes (19): Static knowledge injection at agent build time.  A `KnowledgePack` loads markdow, KnowledgePack, KnowledgePackError, Filesystem-backed knowledge pack loader.  Layout (all keys optional — missing su, Raised when a pack cannot be loaded (missing dir, bad JSON, etc.)., An immutable bundle of static knowledge loaded from a directory.      Use `Knowl, One system message per markdown file, in filename order., All markdown blocks merged into a single system message.          Returns None i (+11 more)

### Community 6 - "KOL Strategy Agent"
Cohesion: 0.12
Nodes (37): build_kol_copytrade(), Build and compile the KOL copy-trade graph.      Args:         knowledge_pack: A, DecisionLog, Graph, int, KnowledgePack, KOLRegistry, LLMClient (+29 more)

### Community 7 - "Backtester & Runner"
Cohesion: 0.12
Nodes (36): Backtester, Runs a graph over a dataset and returns a :class:`BacktestResult`., main(), LLMResult, Message, Example: backtest the scanner over a small historical dataset.  Runs offline (st, _StubLLM, HistoricalCase (+28 more)

### Community 8 - "Core Graph & Edges"
Cohesion: 0.13
Nodes (31): Condition, Edge, Conditional transitions between nodes., A directed, optionally conditional transition.      The engine evaluates a node', GraphExecutionError, GraphValidationError, The graph engine: compile nodes + edges into a runnable agent.  Routing rule: if, Raised at compile time when the graph is structurally invalid. (+23 more)

### Community 9 - "State Machine & Memory"
Cohesion: 0.12
Nodes (33): Hooks, Optional callbacks fired around each node. Sync or async are both fine., Data flowing through the graph.      Attributes:         context: Input supplied, State, Emit, main(), Example: scanner + observability (logging hooks) + memory (blacklist, decision l, _StubLLM (+25 more)

### Community 10 - "Examples & Shared Types"
Cohesion: 0.06
Nodes (61): ProviderConfig, Provider configuration.  Config stores only the *names* of environment variables, Describes one OpenAI-compatible provider., Resolve keys. Literal ``keys`` win (testing); else read ``key_envs`` from env., KeyPool, Mandatory API-key pool with rotation.  Free-tier providers rate-limit aggressive, Round-robin pool of API keys with per-key cooldown on rate limit., OpenAICompatibleClient (+53 more)

### Community 11 - "Scanner Agent & Analyst"
Cohesion: 0.12
Nodes (33): build_scanner(), Build and compile the AI-first scanner graph.      With an LLM client the flow i, neutral_analysis(), Conservative fallback when the LLM is unavailable.      Returns a skip recommend, DecisionLog, Graph, int, KnowledgePack (+25 more)

### Community 12 - "Analyst Prompt Engine"
Cohesion: 0.22
Nodes (16): _pack(), Path, Integration tests: KnowledgePack injection into scanner / sniper prompts., When no pack and no lessons are present, output equals analyst_prompt., An empty pack adds no blocks; output equals analyst_prompt., _SnipeLLM, test_empty_pack_behaves_like_default_prompt(), test_make_analyst_prompt_prepends_pack_blocks() (+8 more)

### Community 13 - "Auth & Subscription"
Cohesion: 0.10
Nodes (26): Subscription auth seam that gates access to the Zetryn agent + models., Entitlement, License, LocalSubscriptionAuth, Subscription auth seam.  Gates access to the Zetryn agent + hosted models. The d, Lightweight, cached license validation — NOT per-run.      Validates once, cache, Result of verifying a subscription key., Verifies a subscription key and returns what it entitles. (+18 more)

### Community 14 - "Router Tier & Tests"
Cohesion: 0.07
Nodes (32): _build_router(), _discover_keys(), str, Example: scanner driven by `LLMRouter` with multi-provider failover.  This is th, Fallback when no provider keys are configured., Return (client, entry_names). client implements the LLMClient protocol., _StubLLM, get_free_tier_limit() (+24 more)

### Community 15 - "Capabilities & Docs"
Cohesion: 0.11
Nodes (24): Agent A — Scanner, Agent B — Sniper, AI-First Design Philosophy, build_scanner, Decision, DecisionLog, Strict Dependency Rule, FullAnalysis (+16 more)

### Community 16 - "Agent Registry & Graph"
Cohesion: 0.19
Nodes (24): Agent A — the memecoin scanner + scorer (M8 AI-first).  Flow (M8 pivot to AI-fir, Agent B — the auto-snipe agent.  Speed-first. Modes selected via ``SniperConfig., Graph, A directed graph of nodes that runs to produce a final ``State``., Deterministic step backed by a plain Python function.      The function mutates, RuleNode, build_linear(), Graph (+16 more)

### Community 17 - "KOL Nodes & Fast Market"
Cohesion: 0.07
Nodes (60): bool, float, KnowledgePack, KOLAnalystVerdict, KOLRegistry, LLMClient, Message, _abort() (+52 more)

### Community 18 - "Sniper Agent"
Cohesion: 0.12
Nodes (27): build_sniper(), Build and compile the sniper graph.      If ``llm_client`` is None (or config ke, Graph, KnowledgePack, LLMClient, str, _AuditLLM, _ctx() (+19 more)

### Community 19 - "Tool Use Node & Tests"
Cohesion: 0.06
Nodes (55): ToolRegistry, Tests for the LLM tool-use loop and ToolUseNode., Tool errors do not crash the loop — they become a tool-role message., A model emitting malformed tool args is reported as tool failure, not crash., Model that never stops calling tools is bounded by max_iterations., Returns canned LLMResult objects in sequence, optionally raising., Realistic flow: model calls a tool, then emits a final JSON verdict., When the loop raises an LLMError, fallback_fn is applied. (+47 more)

### Community 20 - "KOL Confirmed Mode Tests"
Cohesion: 0.18
Nodes (24): _ctx(), _pack(), K5 tests — KOL copy-trade `confirmed` mode (LLM analyst before sizing).  Uses sc, Analyst approves at multiplier=1.0 → final size = rule size., multiplier=0.5 cuts the rule size in half., multiplier=1.5 boosts above rule size (still clamped at max_size)., approve=False → action becomes 'skip' even though rules approved., LLM error → neutral_kol_verdict fallback (approve True, mult 1.0). (+16 more)

### Community 21 - "Decision Log & Reflection"
Cohesion: 0.18
Nodes (8): Anything the engine can execute as a sub-graph (duck-typed Graph)., Runnable, Protocol, RuleFn, Any, Command, State, str

### Community 22 - "Sniper Nodes & Decisions"
Cohesion: 0.09
Nodes (48): ConfluenceVerdict, Decision, GraduationVerdict, confluence_guardrail(), confluence_result(), _latency_ms(), Deterministic sizing → buy Decision (terminal rule node).      Sizing formula:, Deterministic rails the LLM cannot breach (hybrid mode). (+40 more)

### Community 23 - "KOL Reflective Loop Tests"
Cohesion: 0.18
Nodes (23): _CapturingLLM, _ctx(), _pack(), DecisionLog, Path, K7 tests — KOL Copy-Trade x ReflectiveNode integration.  The reflective loop:, Write 3 KOL copy-trade losers with a common 'exit_pattern' feature     that the, Rule mode should accept (and ignore) decision_log without error. (+15 more)

### Community 24 - "LLM Router & Entry Tests"
Cohesion: 0.13
Nodes (21): _AuditLLM, _ctx(), _event(), _FakeLLM, ConfluenceContext, ConfluenceEvent, LLMResult, Tests for Smart Money Confluence mode wiring (v0.14.0 / S5). (+13 more)

### Community 25 - "Community 25"
Cohesion: 0.14
Nodes (12): KOLProfile, KOLRegistry, Any, bool, float, int, KnowledgePack, str (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (14): _infer_feature_keys(), _is_numeric(), Pattern, _quartile_label(), Reflective node: read past decisions, extract loss patterns, inject lessons.  `R, Pick top-level keys that look like features (not run_id / action / outcome)., One observed loss pattern: a (feature, bucket) pair with stats., Return a coarse bucket label for `v` based on the population `values`. (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.19
Nodes (20): _ctx(), _pack(), K4 end-to-end tests for build_kol_copytrade (rule mode)., Caller can pre-build a registry (e.g. assembled from multiple sources)., No whitelist → graph still compiles; runs reject with skip., test_below_deployment_min_hit_rate_skipped(), test_builder_accepts_empty_pack_gracefully(), test_builder_requires_pack_or_registry() (+12 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (30): _llm_client(), main(), _make_event(), GraduationEvent, LLMResult, Message, str, Example: Pump.fun graduation snipe agent (v0.12.0).  Offline by default (stub LL (+22 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (17): Integration tests: ReflectiveNode wired into the scanner closes the learning loo, Reflect must not waste a memory read on tokens rejected by hard gates., Layering order: pack blocks first, then lessons, then analyst persona., reflect_window caps how many past records are summarised., Without an LLM, the reflect node makes no sense — it must not be added., Captures the messages the analyst sees so we can assert injection., Backwards-compat: an LLM-only build does not run the reflect node., With an empty log, reflect runs but lessons_text says 'no prior'. (+9 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (17): Any, make_confluence_gate(), Factory: binds an optional `SmartWalletRegistry` to the gate node.      When `re, SmartWalletProfile, bool, float, int, KnowledgePack (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.19
Nodes (9): _expired(), JSONFileStore, Simple cross-run persistence to a single JSON file.      Loads on init, writes o, test_json_file_store_persists(), Any, bool, float, Path (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (25): SmartWalletAccumulation, _acc(), _ctx(), _event(), ConfluenceContext, ConfluenceEvent, float, str (+17 more)

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (7): A-tier — validated, narrower constraints, C-tier — rejected with reason (do NOT re-propose without new evidence), Notes, S-tier — proven by mainstream Solana pro traders, Solana Memecoin Strategy Catalog, Three-question gate for proposing a new strategy, Tier rubric

### Community 34 - "Community 34"
Cohesion: 0.23
Nodes (13): _build_llm(), _discover_keys(), _load_env_file(), main(), print_analysis(), print_input(), print_output(), print_processing() (+5 more)

### Community 35 - "Community 35"
Cohesion: 0.12
Nodes (39): LifecycleVerdict, _audit_prompt(), _decision(), emergency_exit(), _facts(), _hard_emit(), _hard_short_circuit_target(), hard_stop_loss() (+31 more)

### Community 36 - "Community 36"
Cohesion: 0.04
Nodes (76): LLMResult, Message, LLMResult, Message, LLMResult, Message, LLMResult, Message (+68 more)

### Community 37 - "Community 37"
Cohesion: 0.06
Nodes (71): build_lifecycle(), Build and compile the position-lifecycle graph.      Signature mirrors `build_sn, _llm_client(), main(), LLMResult, Message, Example: position-lifecycle helpers (v0.13.0 / PL1).  Offline by default (stub L, _StubLLM (+63 more)

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
Cohesion: 0.20
Nodes (17): _CapturingLLM, _ctx(), _event(), DecisionLog, GraduationContext, GraduationEvent, LLMResult, Graduation × ReflectiveNode integration tests (v0.12.0). (+9 more)

### Community 42 - "Community 42"
Cohesion: 0.32
Nodes (11): _build_router(), _decide(), _discover_keys(), _load_env_file(), main(), KOLContext, Path, str (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (8): [0.11.0] — 2026-06-27, [0.12.0] — 2026-06-27, Added, Added, Added, Fixed, Notes, Notes

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (20): 0. Context, 1. What This Solves, 2. Framework Boundary, 3.1 `GraduationEvent`, 3.2 `GraduationConfig`, 3.3 `GraduationContext`, 3.4 `GraduationVerdict`, 3. Schema (`trading/schemas.py`) (+12 more)

### Community 45 - "Community 45"
Cohesion: 0.16
Nodes (27): build_graduation(), Agent D — Pump.fun graduation snipe (v0.12.0).  When a Pump.fun token graduates, Build and compile the graduation snipe graph.      Signature mirrors ``build_sni, Graph, int, DecisionLog, KnowledgePack, LLMClient (+19 more)

### Community 46 - "Community 46"
Cohesion: 0.15
Nodes (14): main(), Example: how a bot calls the zetryn scanner.  Runs fully offline with a stub LLM, _StubLLM, _EchoLLM, main(), Path, Example: run the scanner with a deployment-specific KnowledgePack.  A `Knowledge, Stub LLM that echoes the system prompt it received via the reasoning field. (+6 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (18): 1. Capability Matrix, 2. Gap Analysis (before P1–P4), 3. Foundation Work to Do Before P1, 4. Summary, 5. M8 closeout — Scanner v2 hardening, 6. Roadmap, ~~F1. `KnowledgePack` loader~~ — **Done (2026-06-24)**, ~~F2. `ReflectiveNode`~~ — **Done (2026-06-24)** (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (17): Architecture, Auth seam (`zetryn/auth/`), Backtest (`zetryn/backtest/`), Commands, Commit identity (ROLLING RANDOM — no need to ask), Core engine (`zetryn/core/`), Dependency rules (strict), Documentation conventions (MUST FOLLOW) (+9 more)

### Community 49 - "Community 49"
Cohesion: 0.20
Nodes (17): _abort(), _audit_prompt(), _confluence_facts(), confluence_prompt(), _lessons_block(), make_audit_dispatch(), make_confluence_prompt(), market_gate() (+9 more)

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (4): KeyPool, LLMRouter, OpenAICompatibleClient, ProviderConfig

### Community 51 - "Community 51"
Cohesion: 0.16
Nodes (25): AuditVerdict, Command, _abort(), _audit_prompt(), _grad_facts(), _grad_lessons_block(), graduation_gate(), graduation_prompt() (+17 more)

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
Cohesion: 0.16
Nodes (14): ConfluenceConfig, _build_event(), _build_registry(), main(), ConfluenceEvent, LLMResult, Message, SmartWalletRegistry (+6 more)

### Community 71 - "Community 71"
Cohesion: 0.15
Nodes (12): Blacklist, A generic blacklist built on a MemoryStore.  Keys (token mints, dev wallets, any, A generic decision log built on a MemoryStore.  Stores one record per run (plain, Persistent memory: pluggable key-value store + blacklist + decision log., MemoryStore, Persistent memory: a small key-value interface with pluggable backends.  The fra, Namespaced key-value store., test_blacklist() (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.27
Nodes (11): system(), analyst_prompt(), _lessons_block(), make_analyst_prompt(), AI analyst — the single LLM call that drives M8 scanner decisions.  Replaces the, Return a system message with the reflection summary, or None if absent., Return a prompt builder that prepends a knowledge pack + lessons block.      Lay, KnowledgePack (+3 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (16): 0. Summary, 1. Boundary recap, 2. Schemas (`trading/schemas.py`), 3. SmartWalletRegistry (`strategies/smart_wallet_registry.py`), 4. Graph design, 5. Decision modes, 6. Open questions resolved, `ConfluenceConfig` (+8 more)

### Community 76 - "Community 76"
Cohesion: 0.22
Nodes (18): Pure function: derive loss patterns from a list of decision records., Output of a single reflection pass — what gets written to scratch., reflect(), ReflectionResult, float, str, Tests for the ReflectiveNode and underlying `reflect()` extractor., _record() (+10 more)

### Community 77 - "Community 77"
Cohesion: 0.19
Nodes (14): Graph node: load recent decisions and write a lessons block to scratch.      Wri, ReflectiveNode, InMemoryStore, Zero-setup dict-backed store. Default for tests and ephemeral runs., Tests for the M4 memory layer., test_decision_log_and_stats(), test_inmemory_put_get_delete(), test_inmemory_ttl_expiry() (+6 more)

### Community 78 - "Community 78"
Cohesion: 0.22
Nodes (14): _build_clients_by_provider(), _discover_keys(), _load_env_file(), main(), Path, str, KOL Copy-Trade with TIER_SPEED / TIER_QUALITY / TIER_VOLUME router presets.  v0., Build a client per provider, only for those with keys in env.      Returns a dic (+6 more)

### Community 79 - "Community 79"
Cohesion: 0.31
Nodes (10): NarrativeScore, narrative_prompt(), neutral_narrative(), Prompt builder + fallback for the narrative LLM advisor node.  Prompts are kept, Conservative fallback when the LLM is unavailable., Exception, Message, State (+2 more)

### Community 80 - "Community 80"
Cohesion: 0.23
Nodes (7): DecisionLog, Aggregate counts by action and PnL stats from recorded outcomes., Any, MemoryStore, str, Command, State

### Community 82 - "Community 82"
Cohesion: 0.18
Nodes (15): Path, str, Tests for K1 (KOL schemas) and K2 (KOLRegistry from KnowledgePack)., _seed_pack(), test_kol_buy_event_rejects_negative_size(), test_kol_buy_event_required_fields(), test_kol_profile_defaults_are_safe(), test_kol_profile_validates_hit_rate_range() (+7 more)

### Community 83 - "Community 83"
Cohesion: 0.40
Nodes (3): Captures the messages sent to the LLM so we can assert injection., _RecordingLLM, test_scanner_without_pack_works_as_before()

### Community 84 - "Community 84"
Cohesion: 0.25
Nodes (8): [0.5.0] — 2026-06-25, [0.6.0] — 2026-06-25, Added, Added, Changed, Changed, Notes, Notes

### Community 85 - "Community 85"
Cohesion: 0.50
Nodes (3): main(), Example: the auto-snipe agent in pure-rule (fast) vs LLM/hybrid mode.  Shows the, _StubLLM

### Community 87 - "Community 87"
Cohesion: 0.40
Nodes (5): [0.7.0] — 2026-06-25, Added, Changed, Notes, Verified end-to-end

### Community 88 - "Community 88"
Cohesion: 0.40
Nodes (5): [0.9.0] — 2026-06-26, Added, Backwards compatibility, Notes, Verified end-to-end

### Community 89 - "Community 89"
Cohesion: 0.25
Nodes (7): [0.1.0] — 2026-06-24, [0.4.0] — 2026-06-25, Added, Added, Changed, Changelog, Notes

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
Cohesion: 0.22
Nodes (13): _build_provider(), _build_router_client(), _discover_keys(), _load_env_file(), main(), int, LLMClient, ProviderConfig (+5 more)

### Community 94 - "Community 94"
Cohesion: 0.50
Nodes (4): [0.8.0] — 2026-06-25, Added, Backwards compatibility, Notes

### Community 95 - "Community 95"
Cohesion: 0.33
Nodes (12): Path, str, Tests for KnowledgePack (markdown + JSON loader)., test_as_system_message_joins_with_separator(), test_from_dir_bad_json_raises(), test_from_dir_empty_dir_yields_empty_pack(), test_from_dir_loads_json_data(), test_from_dir_loads_markdown_in_filename_order() (+4 more)

### Community 96 - "Community 96"
Cohesion: 0.26
Nodes (11): build_confluence(), Agent E — Smart Money Confluence (v0.14.0 / S5).  Fires when ≥ N pre-vetted smar, Build and compile the Smart Money Confluence graph.      Signature mirrors ``bui, DecisionLog, int, KnowledgePack, LLMClient, SmartWalletRegistry (+3 more)

### Community 97 - "Community 97"
Cohesion: 0.29
Nodes (4): Agent C — KOL Copy-Trade.  Consumes a `KOLContext` and emits a `Decision`. The b, Agent E — Position Lifecycle Helpers (v0.13.0 / PL1).  First position-management, Reference strategies built on the zetryn framework.  This is the proving ground:, Typed lookup of KOL profiles from a `KnowledgePack`.  The bot ships a `kol_white

### Community 98 - "Community 98"
Cohesion: 0.40
Nodes (5): [0.13.0] — 2026-06-27, [0.14.0] — 2026-06-27, Added, Design notes, Design notes

## Knowledge Gaps
- **200 isolated node(s):** `Added`, `Design notes`, `Added`, `Fixed`, `Added` (+195 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State` connect `State Machine & Memory` to `LLM Client & Guardrails`, `KOL Copy-Trade Example`, `KOL Strategy Agent`, `Core Graph & Edges`, `Examples & Shared Types`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Agent Registry & Graph`, `KOL Nodes & Fast Market`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `Decision Log & Reflection`, `Sniper Nodes & Decisions`, `KOL Reflective Loop Tests`, `Community 26`, `Community 27`, `Community 29`, `Community 34`, `Community 36`, `Community 38`, `Community 39`, `Community 40`, `Community 42`, `Community 46`, `Community 54`, `Community 55`, `Community 72`, `Community 76`, `Community 77`, `Community 78`, `Community 79`, `Community 80`, `Community 85`, `Community 86`, `Community 93`, `Community 99`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `LLMResult` connect `Community 36` to `LLM Client & Guardrails`, `KOL Audit Mode Tests`, `Rate Limit & LLM Router`, `KOL Strategy Agent`, `Backtester & Runner`, `State Machine & Memory`, `Examples & Shared Types`, `Scanner Agent & Analyst`, `Analyst Prompt Engine`, `Router Tier & Tests`, `Sniper Agent`, `Tool Use Node & Tests`, `KOL Confirmed Mode Tests`, `KOL Reflective Loop Tests`, `Community 29`, `Community 34`, `Community 40`, `Community 46`, `Community 83`, `Community 85`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `State` connect `Community 35` to `Community 96`, `Community 32`, `Community 37`, `Community 41`, `Community 45`, `Community 49`, `KOL Nodes & Fast Market`, `Community 51`, `Sniper Nodes & Decisions`, `LLM Router & Entry Tests`, `Community 59`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Are the 180 inferred relationships involving `LLMResult` (e.g. with `LLMResult` and `Message`) actually correct?**
  _`LLMResult` has 180 INFERRED edges - model-reasoned connections that need verification._
- **Are the 206 inferred relationships involving `Message` (e.g. with `DecisionFallbackFn` and `LLMResult`) actually correct?**
  _`Message` has 206 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `State` (e.g. with `Condition` and `Edge`) actually correct?**
  _`State` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `LLMError` (e.g. with `DecisionFallbackFn` and `GuardrailFn`) actually correct?**
  _`LLMError` has 102 INFERRED edges - model-reasoned connections that need verification._