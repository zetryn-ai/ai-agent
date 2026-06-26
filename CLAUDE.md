# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Framework Boundary (NON-NEGOTIABLE — read first, every session)

**Zetryn Trading is an AI Agent Framework / library.** Public users (their
bots) consume it: they push input (already-filtered or not), the framework
returns a `Decision`, and the bot acts on it. Nothing in this repository
should ever try to *fetch data*, *subscribe to feeds*, *hold keys*, *sign
transactions*, *track positions*, or *execute trades*. All of that is the
caller's responsibility.

| The framework DOES | The user's bot DOES |
|---|---|
| Define input/output schemas (`TokenInput`, `KOLContext`, `Decision`, …) | Fetch / stream / enrich the data and fill those schemas |
| Orchestrate the decision graph (nodes, edges, LLM calls, tool-use loops) | Subscribe to Helius / Cielo / GMGN / WS / RPC feeds |
| Run LLM analyst calls and forward `tools` to providers | Implement each `Tool`'s async function against its data source |
| Read `KnowledgePack` files the user shipped | Author & maintain those files (KOL whitelists, rules, lessons) |
| Read `DecisionLog` for reflection / lessons | Call `record_outcome` after the trade is executed |
| Return a `Decision` (action, size, reasons, flags) | Execute the trade, sign tx, manage slippage / MEV / position lifecycle |
| Hold per-run state in `State.scratch` | Hold cross-run state (positions, cooldowns, watchlists) and pass via context |

**Practical implications when designing or coding here:**
- New schema field? Probably yes. New async fetcher inside `zetryn/`? **No.**
- New rule node that reads `state.context.token.X`? Probably yes. New rule
  node that opens a network connection? **No.**
- New `Tool` definition (schema + example stub)? Yes. New `Tool` that
  hard-codes a real API client to Helius? **No** — show the stub in
  `examples/`, never wire production credentials inside the framework.
- "The strategy needs X" is always shorthand for "the framework defines X's
  shape; the bot supplies it". If any code or doc reads otherwise, it's a
  bug — flag it.

This boundary is reaffirmed at design-doc level in
[`docs/plans/2026-06-25-kol-copytrade-strategy.md §0.5`](docs/plans/2026-06-25-kol-copytrade-strategy.md).
If the boundary ever conflicts with an apparent feature request, ask
the user to clarify before crossing it.

## Commit identity (MUST ASK BEFORE EVERY COMMIT/PUSH/PR)

The user actively uses **three** GitHub identities with distinct PATs,
wired as three separate MCP servers:

| MCP server | Tool prefix | Identity | When to use |
|---|---|---|---|
| `github@aldirrss` | `mcp__github_aldirrss__*` | personal `aldirrss` | personal repos / commits authored as the user |
| `github@cry` | `mcp__github_cry__*` | alternate `cry` | as decided per task |
| `github@zetryn` | `mcp__github_zetryn__*` | org `zetryn` | commits to `zetryn/*` repos that should appear as authored by zetryn |

**Hard rule:** before any `git commit`, `git push`, or PR creation,
**ASK the user which identity to use.** Do NOT default to a previously
used identity, do NOT infer from the working directory or remote name.
The user explicitly stated they will be actively rotating between all
three — silent defaults will produce wrong commit attribution.

Phrase the question crisply, e.g.:
> "Mau commit ini pakai MCP yang mana — `aldirrss`, `cry`, atau `zetryn`?"

Implications by chosen identity:
- **Local `git commit` + `git push`** → author resolves from
  `git config user.email` (currently `aldirrss`). Use this when the
  user picks `aldirrss`.
- **`mcp__github_zetryn__push_files`** → server-side commit signed as
  `zetryn`, auto-Verified badge in the GitHub UI.
- **`mcp__github_cry__push_files`** → server-side commit signed as
  `cry`, same Verified treatment.

This rule overrides any earlier session-level pattern. Do not skip it
even for "tiny" commits — the user prefers a one-line clarifying
question over a wrong-author commit landing on `main`.

## Commands

```bash
# Install in editable dev mode (always do this first)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a specific test file
pytest tests/test_core_graph.py

# Run a specific test
pytest tests/test_core_graph.py::test_simple_graph

# Lint
ruff check .
ruff format .

# Run a walkthrough (offline, no API key needed — uses stub LLM)
cd examples && python walkthrough.py

# Run the scanner example (needs a provider key in .env)
cd examples && python run_scanner.py
```

## Architecture

`zetryn` is a **graph-based AI agent framework**. It decides; the caller executes. It never holds a private key or touches the chain.

```
BOT -> gather data -> decision = agent.run(State(context=ctx)) -> BOT executes
                           |
               ZETRYN (graph engine + advisor LLM)
```

### Dependency rules (strict)

```
zetryn/   ← no imports from trading/ or strategies/
trading/  ← no imports from zetryn/ or strategies/  (pure contract/schemas)
strategies/ ← imports both zetryn/ and trading/
```

Only `zetryn/` is packaged into the wheel. `strategies/` is the proving ground (demo + tests).

### Core engine (`zetryn/core/`)

Four primitives that compose everything:

- **`State`** — data flowing through a run: `context` (bot input, opaque), `scratch` (mutable inter-node dict), `output` (final result), `trace` (per-node snapshots), `run_id`.
- **`Node`** — a Protocol with `name: str` and `async run(state) -> Command | None`. Three concrete types: `RuleNode` (pure function), `LLMNode` (in `zetryn/llm/`), `AgentNode` (sub-graph).
- **`Edge`** — conditional transition. Static routing uses declared edges; dynamic routing uses `Command.goto` returned from a node (wins over static edges).
- **`Graph`** — compiles nodes + edges, validates at compile time (before money moves), then runs. `max_steps=100` guards against unbounded loops. `END` sentinel terminates the run.

Node execution pattern: engine snapshots `scratch` before each node → node mutates `scratch` and/or returns `Command` → engine appends `StepTrace` → moves to next node.

### LLM layer (`zetryn/llm/`)

- **`LLMClient`** protocol: `complete(messages, *, model, temperature, json_mode) → LLMResult`.
- **`OpenAICompatibleClient`** — one adapter covers Groq, OpenRouter, Gemini. All free-tier by default.
- **`KeyPool`** — rotates multiple API keys on 429 to multiply free-tier quota.
- **`ProviderConfig`** — stores env var *names* (`key_envs`), never key values. Resolved at build time; missing keys fail fast.
- **`LLMNode`** — wraps an `LLMClient` call with structured output (Pydantic schema), retry/backoff, and graceful fallback (returns neutral score + `llm_failed` flag, never crashes).
- **`ZetrynClient`** (`zetryn/llm/zetryn_client.py`) — client for hosted Zetryn models (Hardes/Medifus/Easfus). Requires a subscription key; currently backed by `LocalSubscriptionAuth` stub.

### Tools (`zetryn/tools/`)

Read-only capabilities injectable by the bot. Each `Tool` has a Pydantic input schema and an async function. Registered in `ToolRegistry`. LLM decides when to call; the engine executes. Errors are graceful (empty result + flag, never crash).

### Memory (`zetryn/memory/`)

- **`MemoryStore`** protocol: `get/put/delete/query` namespaced by `ns` string.
- **`InMemoryStore`** — zero-setup, for tests and ephemeral runs.
- **`JSONFileStore`** — simple cross-run persistence to a JSON file.
- **`Blacklist`** — known rug tokens/dev wallets → instant `skip`, saves LLM calls.
- **`DecisionLog`** — every decision + outcome, used for backtest metrics.

### Observability (`zetryn/observability/`)

Structured per-node logging as JSON. `Hooks` protocol (`on_node_start`, `on_node_end`, `on_node_error`) passed into `graph.run(state, hooks=...)`. `trace_to_dicts()` serializes trace for logging/backtest.

### Auth seam (`zetryn/auth/`)

`SubscriptionAuth` protocol → `LocalSubscriptionAuth` (stub, validates any non-empty key) → `RemoteSubscriptionAuth` (future, calls Zetryn platform). `License` wraps auth with TTL caching and grace-period on transient failures. Plan tiers: free / basic / pro / max, each with per-model rate limits (TPM/RPM/RPD) for Easfus/Medifus/Hardes.

### Backtest (`zetryn/backtest/`)

`Backtester.run(items)` runs the compiled graph over a list of `(id, context)` pairs and returns `BacktestResult`. Test/backtest/live are identical graph runs — just different `DataProvider` implementations injected by the bot.

### Trading domain (`trading/schemas.py`)

Shared contract: `TradingContext`, `Decision`, `DataProvider` protocol, market/holder/contract/social data shapes, `ScannerConfig`, `SniperConfig`. This is the *shape agreement* between the bot and the framework.

### Strategies (`strategies/`)

- `strategies/providers.py` — `MockDataProvider` and sample fixtures for offline tests/demos.
- `strategies/nodes/` — `filters.py` (rule nodes: safety, market, social filters), `decide.py` (aggregate → `Decision`), `prompts.py` (narrative LLM prompts), `sniper_nodes.py`.
- `strategies/agents/scanner.py` — `build_scanner(llm)` returns a compiled `Graph`.
- `strategies/agents/sniper.py` — `build_sniper(llm)` returns a compiled `Graph`.

## Key patterns

**Adding a new node:** write a plain function `(state: State) -> Command | None`, wrap in `RuleNode("name", fn)`, register with `graph.add_node(...)` and connect with `graph.add_edge(...)`.

**Structured LLM output:** define a Pydantic model for the schema, pass it to `LLMNode`. The node enforces JSON mode, validates, and retries automatically.

**Prompts as assets:** prompts live in `strategies/nodes/prompts.py`, not hardcoded in node logic.

**Graceful degradation:** LLM failures → `llm_failed` flag in scratch + neutral score. Tool errors → empty result + error flag. Graph never crashes on transient external failures.

**Testing without credentials:** use `InMemoryStore`, `MockDataProvider` (in `strategies/providers.py`), and a stub `LLMClient` (see `examples/walkthrough.py`). No wallet/RPC/API key needed.
