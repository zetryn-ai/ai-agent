# Zetryn Agent Framework — Design

**Date:** 2026-06-23
**Status:** Approved (brainstorming complete), implementation in progress

> **Update 2026-06-24:** Sections **2 (Key Decisions — LLM role row)**, **5 (LLM Layer)**, and **9 (Use-Case Mapping)** are partially superseded by [2026-06-24-ai-first-pivot.md](2026-06-24-ai-first-pivot.md), which reframes the framework as AI-first (LLM as primary analyst, rules as hard gates + guardrails). All other sections of this document — core engine, memory, observability, boundary, dependency rules, project structure, auth seam, business model — **remain authoritative**.

## 0. Product Vision & Brand

Full-stack play, modeled on Anthropic:

| Anthropic | This project | Role |
|---|---|---|
| Anthropic | **Lema** | The company |
| Claude | **Zetryn** | The AI brand |
| Opus / Sonnet / Haiku | **Hardes / Medifus / Easfus** | LLM models (fine-tuned from open models; served + on HuggingFace) |
| Claude Code | **Zetryn Trading** | The agent/framework (this repo), trading-focused |
| `ANTHROPIC_API_KEY` | **subscription (login at zetryn site / subs code)** | Monetization gate |

**Business model:** the framework is the client; developers `import zetryn` and use it
in their *own* bots, but accessing Zetryn's models requires a **subscription**. They
can run LLM-decide, advisor, or hybrid modes. This sidesteps the alpha-decay and
financial-advice problems of selling signals — Zetryn sells *reasoning infrastructure*,
not trade calls.

**Provider tiers (LLM):**
1. Zero-cost (default for dev): Groq, Gemini, OpenRouter — via `OpenAICompatibleClient`.
2. Paid (next level): OpenAI (OpenAI-compatible), Anthropic (native adapter later).
3. Zetryn models: `ZetrynClient` → Hardes/Medifus/Easfus, gated by subscription auth.

**Monetization seam (built now as a stub):**
- `zetryn/auth/` — `SubscriptionAuth` protocol + `Entitlement`; `LocalSubscriptionAuth`
  validates locally for dev. Real enforcement is server-side at the Lema/Zetryn platform
  (`RemoteSubscriptionAuth` replaces the stub without touching callers).
- `zetryn/llm/zetryn_client.py` — `ZetrynClient` is an `LLMClient` for Zetryn models,
  built lazily after the subscription verifies. Until the platform is live, point its
  `base_url` at a self-hosted vLLM/TGI serving the fine-tuned model.

**Three parallel workstreams** (don't block the framework on the models):
1. Framework (this repo) — works with any provider today.
2. Models (Hardes/Medifus/Easfus) — fine-tune open models, serve via vLLM, push to HF.
3. Platform — auth + subscription + billing + hosted serving + observability dashboard.

## 1. Purpose & Scope

`zetryn` is a Python **AI agent framework** (generic, reusable) whose first proving
use-case is **Solana memecoin trading**. It is a *library* that a trading bot calls —
not the bot itself. Developers consume it as an SDK; the hosted platform (subscription)
gates access to Zetryn's own models.

**North star:** framework-first. Every abstraction must be justified by at least one
real trading use-case. YAGNI is enforced ruthlessly.

## 2. Key Decisions

| Aspect | Decision |
|---|---|
| Focus | Framework-first; trading is the proving use-case |
| Language | Python (pure core). Dashboard (TS/Next.js) is out of scope |
| Paradigm | Hybrid: graph foundation; nodes can host sub-agents (built later) |
| LLM role | Advisor by default; node interface supports `rule` and `llm` modes |
| Use-case | Solana memecoin: (A) scanner+scorer, (B) auto-snipe |
| Boundary | Framework only **decides** (signal/decision). Bot owns wallet/RPC/execution |

## 3. Architecture & Boundary

The framework is **stateless toward the chain** and **never holds a private key**.
It receives data and returns a decision. The bot owns the real world.

```
BOT (yours): RPC/Wallet/Hot-loop -> gather data -> decision = agent.run(TradingContext)
                                                      |
                                          ZETRYN (graph engine + nodes)
                                          scan -> filter -> analyze -> risk -> decide
                                                      |
                                    Decision{action, size, confidence, reasons[]}
                                                      |
                                    BOT executes (buy/sell/skip)
```

- **Framework owns:** graph orchestration, state management between nodes, LLM
  (advisor) calls, scoring, signal aggregation, memory, observability/tracing.
- **Bot owns:** all chain I/O (RPC, mempool, prices), wallet & signing, execution,
  hot-loop timing, and **supplying data** to the framework via a context object.
- **Gray zone (data fetching):** the framework *defines* the `DataProvider` interface;
  the bot *injects* the implementation. The framework knows the *shape* of data, not
  its *source*.

**Payoff:** the framework can be unit-tested and backtested with no wallet/RPC at all,
and stays chain-agnostic.

## 4. Core Engine (Graph)

Four minimal primitives. Build these first; YAML authoring layer comes later.

- **`State`** — data flowing through the graph: `context` (bot input), `scratch`
  (inter-node results), `decision` (final output), `trace` (per-node snapshots).
- **`Node`** — single step. One `Protocol`: `async def run(state) -> State | Command`.
  Concrete: `RuleNode` (deterministic), `LLMNode` (advisor call), `AgentNode`
  (extension point for sub-agent / multi-agent panel — built later).
- **`Edge`** — conditional transition between nodes. Supports branching and bounded
  loops.
- **`Graph`** — compiles nodes + edges into a runnable agent. Includes a **validator**
  (orphan nodes, edges to missing nodes, dead-ends, unbounded loops) that runs at
  compile time — before any money moves.

### State model: hybrid mutable + auto-snapshot
Inside a node function you may mutate `s.scratch['x'] = ...` (ergonomic). The engine
takes an **automatic snapshot before each node** -> full `trace` for audit/resume/backtest.

### Routing: YAML for static, Command for dynamic
- Static flow (90%): declarative edges (later in YAML; in code for now).
- Dynamic flow: a node may **return a `Command`** to override route + update state at
  runtime (escape hatch for LLM/agent nodes).
- Rule: no Command returned -> engine uses the declared edge. Command returned ->
  `goto` wins.

```python
def score(s) -> Command:
    r = llm_call(s)
    return Command(update={"llm_score": r.score},
                   goto="buy" if r.score > 0.7 else "watch")
```

### Authoring: code first, YAML later
The minimal primitives are the foundation. The YAML loader is built **after** 2-3
strategies exist in code and the repeating patterns are clear — to avoid designing a
config schema around guesses (inner-platform trap). YAML is deferred, not cancelled.

## 5. LLM Layer (Advisor)

- **`LLMClient`** — thin provider abstraction. First adapter:
  **`OpenAICompatibleClient`** — one adapter covers Groq, OpenRouter, and Gemini
  (OpenAI-compatible endpoint). Anthropic native adapter (prompt caching) added when
  moving to paid.
- **Zero-cost first:** default dev provider = Groq or Gemini Flash (free, fast,
  structured output works). Provider chosen entirely via config.
- **Structured output is mandatory:** every `LLMNode` declares a Pydantic schema;
  the engine forces JSON/tool-calling, validates, and retries on mismatch. For weak
  models without native structured output: fallback to JSON-in-prompt + Pydantic
  validate + retry.
- **Reliability primitives:** timeout + retry w/ backoff; **graceful fallback**
  (on total LLM failure return a neutral score + `llm_failed` flag, never crash);
  prompt caching (Anthropic, later); cost/latency tracked into `trace`.
- **Prompts as assets:** stored modular (file/registry), not hardcoded in nodes, so
  they can be iterated and A/B-tested without touching logic.

### Key management
- Config stores only the **env var name** (`key_env`), never the value.
- Local/dev: `.env` (gitignored) + `.env.example` template; loaded via `python-dotenv`.
- Server/prod: real env vars or secrets manager (same config, different env source).
- **Fail-fast:** missing referenced key errors clearly at startup.
- **Key pool rotation is mandatory:** accept multiple keys per provider
  (`key_envs: [...]`) and rotate automatically on `429` to multiply free-tier quota.

## 6. Tools & Data Interface

Everything here is **read-only / analysis** — no execution tools (those live in the
bot). Two distinct concepts:

- **`DataProvider`** — typed interface for *known* structured data needed by RuleNodes
  (`liquidity`, `holders`, `token_meta`, `price_history`, ...). Framework defines the
  shape; bot injects the implementation (Helius/Birdeye/DexScreener/...).
- **`Tool`** — open-ended capability for LLMNode/AgentNode (e.g. `twitter_sentiment`).
  Each has a Pydantic input schema + async fn, registered in a registry. The LLM
  decides when to call; the engine executes and feeds the result back.

Rules for both: injected by the bot (chain-agnostic preserved); errors are **graceful**
(return empty + flag, never crash); **timeouts mandatory**; **short cache TTL** (memecoin
data goes stale in seconds — cache only dedups calls within one cycle). The framework
ships `MockDataProvider` and `HistoricalDataProvider` for tests and backtests.

## 7. Memory & State

Two tiers. Framework defines the memory interface; backend is pluggable.

- **Working memory (per-run):** `State.scratch` + `trace`. Lives for one cycle.
- **Persistent memory (cross-run):** single `MemoryStore` protocol
  (`get`/`put`/`query`). Backends: default JSON/SQLite -> Redis -> vector (later).

Concrete trading memory (built on `MemoryStore`):
- **`Blacklist`** — known rug tokens & bad dev wallets -> instant skip, saves LLM calls.
- **`DecisionLog`** — every decision + (later) its outcome. Core for evaluation &
  backtest (win-rate, PnL, LLM precision). Bot sends execution results back.
- **`SemanticMemory`** (vector, optional) — recall similar past tokens. Interface ready,
  implementation later (YAGNI).

**Boundary:** the framework does **not** store positions/portfolio — that truth lives in
the bot. If a decision needs current positions (anti double-buy, exposure sizing), the
bot passes them via `TradingContext`. The framework stores *knowledge* (blacklist,
decision history, patterns), not *money state*.

## 8. Observability, Testing & Backtesting

- **Observability:** structured per-node logging (input, output, duration, LLM cost,
  routing) as JSON; run ID per decision; `on_node_start/end/error` hooks (seam to a
  future TS dashboard).
- **Testing:** unit-test each RuleNode (pure fn); `MockDataProvider` + fake `LLMClient`
  for deterministic offline graph tests; snapshot tests over `trace`. Target: graph
  fully testable with no wallet, RPC, or API key.
- **Backtesting:** `HistoricalDataProvider` injects past data; `DecisionLog` + outcomes
  compute metrics; compare graph A vs B on the same dataset before live money. LLM can
  be mocked/cached -> cheap & fast.

**Unifying principle:** because the framework is stateless toward the real world and all
I/O is injected, **test/backtest/live are just different providers** — the graph code is
identical.

## 9. Use-Case Mapping

### Agent A — Scanner + Scorer (advisor, no execution)
```
token_meta -> liquidity_filter -> rug_check -> holder_check
                  | fail            | fail        | fail
                  v                 v             v
                            reject (Decision{action: skip})
   pass all v
   narrative_score (LLM) -> aggregate -> Decision{action: alert|watch|skip, confidence}
```
RuleNodes drop ~90% of junk fast & free; LLM runs only on survivors (saves free-tier
calls). `aggregate` combines rule + LLM scores. `DecisionLog`/`Blacklist` updated.

### Agent B — Auto-Snipe (decision for fast execution)
```
rug_check (<50ms) -> safety_gate -> size_decision -> Decision{buy, size, slippage}
```
Same graph pattern; speed-prioritized. `narrative_score` (LLM) can be disabled via config
for a sub-second pure-rule path. `safety_gate` can `goto="abort"` instantly. Exit /
take-profit / stop-loss are rules in the **bot**; the framework only emits the entry signal
+ parameters.

## 10. Project Structure

```
zetryn-agent-framework/
  zetryn/            # the framework package (installable; no src/ nesting)
    core/            # generic engine (chain-agnostic): state, node, graph, edge
    llm/             # client protocol, openai_compat adapter, keypool
    tools/           # Tool, registry (generic, read-only capabilities)
    memory/          # MemoryStore, Blacklist, DecisionLog (+ vector later)
    providers/       # generic provider helpers (reserved)
    observability/   # trace, logging, hooks
  trading/           # domain CONTRACT only (the shared agreement)
    schemas.py       # TradingContext, Decision, DataProvider protocol, data shapes
  strategies/        # proving ground: how the framework is used
    nodes/           # filters.liquidity, filters.rug, prompts.narrative, decide
    agents/          # scanner.py, sniper.py
    providers.py     # MockDataProvider + sample fixtures (test/backtest/demo)
  tests/
  examples/          # how a bot calls the framework
  pyproject.toml
```
**Dependency rule:** `zetryn` (framework) imports nothing from `trading` or
`strategies`. `trading` is the pure contract (depends on neither). `strategies`
depends on both `zetryn` and `trading`. In production the `strategies` code
typically moves into the bot repo; here it demonstrates and tests the framework.
Only `zetryn` is packaged into the wheel.

## 11. Roadmap

| M | Focus | Status |
|---|---|---|
| M0 | Core engine (State, Node, Graph, Command, snapshot, validator) | ✅ done |
| M1 | LLM layer (OpenAICompatibleClient + key pool + structured output + fallback) | ✅ done |
| M2 | Generic tools (Tool, registry, timeout/graceful) | ✅ done |
| M3 | **Agent A (scanner)** — real graph end-to-end ("first light") | ✅ done |
| M4 | Memory + observability (Blacklist, DecisionLog, hooks, logging, trace) | ✅ done |
| S1 | **ZetrynClient + auth seam** (subscription gate, model tiers, provider tiers, License) | ✅ done (stub) |
| M5 | Backtest (generic Backtester + trading metrics: win-rate, PnL, rug recall) | ✅ done |
| M6 | **Agent B (sniper)** — sub-ms pure-rule path + LLMDecisionNode (decide/hybrid + guardrail) | ✅ done |
| M7+ | Earned later: YAML loader, multi-agent node, vector memory, copy-trade | later |

**Platform workstream (separate from the framework):** P1 RemoteSubscriptionAuth +
hosted serving (vLLM) for one fine-tuned model · P2 billing + tiers + multi-tenant ·
P3 observability dashboard (Next.js) · P4 model improvement loop.

M3 was "first light": a real agent running before adding more. S1 wires the monetization
seam early so the architecture is ready, without blocking the engine.
