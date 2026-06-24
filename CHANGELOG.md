# Changelog

All notable changes to `zetryn-trading` will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
