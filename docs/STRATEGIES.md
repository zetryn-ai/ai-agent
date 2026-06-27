# Solana Memecoin Strategy Catalog

Strategies that are actually used by professional Solana memecoin traders
(validated against mainstream sources, not speculative). Tiered S / A / C
to guide what to build next.

**Scope:** Solana memecoin / DEX, targeted at v1.0.0 release.

| | |
|---|---|
| For build status of each row | see `Implemented` column |
| For roadmap (versions, milestones) | [CAPABILITIES.md §6](CAPABILITIES.md#6-roadmap) |
| For per-strategy design specs | [plans/](plans/) |

---

## Tier rubric

A strategy is rated on four dimensions; the weakest dimension caps the tier.

| Dimension | What it asks |
|---|---|
| **Edge durability** | Is the alpha still there, or has the crowd saturated it? |
| **Signal-to-noise** | What fraction of fired signals are real (vs bait / wash trades / random)? |
| **Data accessibility** | Can the bot get the data with standard public feeds (Helius, Cielo, GMGN, BirdEye)? |
| **Distinctness** | Is the trigger genuinely different from other listed strategies, or a config tweak? |

| Tier | Meaning |
|---|---|
| **S** | All four strong. Mainstream pro traders use it. Build it. |
| **A** | Validated by mainstream sources but with one constraint (narrower window, partial overlap, harder data). |
| **C** | Rejected with reason. Documented to prevent re-proposal. |

B-tier intentionally absent — anything that would land there is either a config knob on an S/A agent or belongs in C.

---

## S-tier — proven by mainstream Solana pro traders

| Strategy | Signal mechanic | Implemented |
|---|---|---|
| **Multi-aspect pre-trade scanner** | AI-first analysis combining safety (contract, holder concentration), market structure, wallet intel, and social signals into a single verdict on a candidate stream. Validated as "real edge is filtering bad setups before swap" (DEXTools 2026). | ✅ [build_scanner](../strategies/agents/scanner.py) |
| **Speed sniper with structural gates** | Sub-ms rule path on pre-filtered tokens; optional LLM decide inside deterministic guardrail. Used universally by competitive Solana bots in 2026. | ✅ [build_sniper](../strategies/agents/sniper.py) |
| **KOL copy-trade (curated)** | Copy buys from a hand-curated whitelist of historically-profitable wallets, sized by per-wallet `hit_rate` × `tier`. Used by GMGN, Cielo, Axiom users as a primary alpha source. | ✅ [build_kol_copytrade](../strategies/agents/kol_copytrade.py) |
| **Pump.fun graduation snipe** | Enter in the 5–30s window after a token graduates to Raydium; gate on bonding-curve fill speed, unique buyers, LP burned, premium %. | ✅ [build_graduation](../strategies/agents/graduation.py) |
| **Smart money confluence (multi-wallet)** | Fire when ≥ N pre-vetted smart wallets accumulate the same token within a rolling window (mainstream tells: "5+ smart wallets scooping a token over a week"). Multi-wallet correlation — much higher precision than single-wallet copy. | ✅ [build_confluence](../strategies/agents/confluence.py) |
| **Early-stage dip buy** (post-launch OR post-graduation) | Wait for the dump wave to settle, then enter when sells thin out, holders retain, and unique-buyer count starts rising again. Two events share one signal mechanic — selected via `event_type ∈ {launch, graduation}`: **launch** = wait 1–10 min for sniper/bundler dump to clear (token still in BC); **graduation** = wait for early-BC-buyer TP wave after Raydium migration. Distinct from speed sniper (waits) and graduation snipe (also waits, opposite direction). | ⬜ not built |

## A-tier — validated, narrower constraints

| Strategy | Signal mechanic | Implemented |
|---|---|---|
| **Organic growth detector** | Watch the post-launch time-series: organic growth = steady climb + healthy pullbacks + rising unique-buyer count. Manipulation tell = vertical line with zero sells. Distinct from snapshot scanner (chart-pattern feature set on time series). Useful as a triage filter that promotes scanner candidates to higher-confidence buys. | ⬜ not built |

A-tier is intentionally short. If a strategy is worth doing, it's almost always S; the few that don't qualify usually overlap heavily with an S row.

## C-tier — rejected with reason (do NOT re-propose without new evidence)

| Strategy | Why rejected |
|---|---|
| **Twitter sentiment as primary trigger** | Lagging signal. By the time sentiment data lands, the move is done. Mainstream sources treat social as confirmation, not trigger. Belongs as scoring input (already in `SocialData`). |
| **Single influencer / KOL mention** | Single-source social signals are noisy and front-runnable. Edge exists only inside multi-source confluence — covered by S-tier "Smart money confluence". |
| **MEV / Jito front-run / sandwich** | Execution-layer concern (transaction ordering, validator tipping), not decision-layer. Edge belongs to lowest-latency RPC and validator relationships, not the framework. Out of scope. |
| **Single whale wallet mirror** | Strict subset of KOL copy-trade. A whale is just an entry in `KOLRegistry` with a different tier label. No new agent needed. |
| **Generic "AI predict price" black box** | No durable edge in memecoins without structural features the S-tier rows already capture. LLM-on-price-history adds noise, not alpha. |
| **Honeypot / rug detection as a "strategy"** | Defensive safety primitive every entry agent already runs. Not a strategy. Lives in the safety layer (`safety_gate` / `fast_safety`). |

---

## Three-question gate for proposing a new strategy

Before drafting a spec, all three must pass.

| # | Question | Fail = |
|---|---|---|
| 1 | **Mainstream-validated** — does at least one credible source (DEXTools, CoinLedger, on-chain analytics blog, prominent trader) describe pro traders using this in 2026 Solana memecoin context? | Speculative — don't add. |
| 2 | **Distinct primary signal** — predictive feature no S/A row uses as primary trigger? "Already a scoring input" doesn't count. | Add as input to existing agent. |
| 3 | **Boundary-safe** — definable without subscribing, holding state, or signing? | Kill at boundary; that's a bot-layer concern. |

Pass all three → add a row at the right tier + open a design doc in [docs/plans/](plans/).

---

## Notes

- **Position management** (TP/SL/scale-out helpers like "sell half at 2x to recoup initials") is NOT a strategy — it's a risk-management primitive universal to every trader. Tracked in [CAPABILITIES.md §6](CAPABILITIES.md#6-roadmap) as PL1.
- **Defensive gates** (rug detection, blacklist, contract safety) are safety primitives every entry agent reuses. Not strategies.
- This catalog is opinionated and tied to the **2026 Solana memecoin meta**. Crowd saturation moves tiers in months — revisit on every release.
