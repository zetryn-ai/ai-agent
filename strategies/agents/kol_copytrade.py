"""Agent C — KOL Copy-Trade.

Consumes a `KOLContext` and emits a `Decision`. The bot subscribes to
KOL wallet events outside the framework, enriches the bought token's
`TokenInput`, and hands the framework a `KOLContext` per event. The
framework decides whether to copy and at what size.

Two modes, selected at build time:

  rule (default — v0.6.0)
    fast_safety → kol_quality → fast_market → sizing → END
    Pure rule, no LLM call. Latency <1ms (target for live).

  confirmed (v0.7.0)
    fast_safety → kol_quality → fast_market → analyst (LLM) → sizing → END
    An LLM analyst sees the full fact sheet AFTER the rules already
    approved the buy. It can:
      - approve the buy with size_multiplier in [0, 1.5]
      - veto the buy entirely (action=skip)
    The analyst is NOT redoing the decision — it is catching qualitative
    red flags the rules cannot encode (e.g. KOL with a dump-into-followers
    pattern, weak confluence, etc.).

Boundary recap (see docs/plans/2026-06-25-kol-copytrade-strategy.md §0.5):
the framework defines + decides; the bot fetches and executes. The KOL
whitelist is loaded by the bot into a `KnowledgePack` and wrapped in
`KOLRegistry`, which this builder accepts. Cool-down state is also
bot-owned (passed in via `KOLContext.last_copy_ts`). When `mode="confirmed"`
the bot also supplies an `LLMClient`.

`audit` mode (rule decides instantly + async LLM verifies) is K6, pending.
"""

from __future__ import annotations

from trading.schemas import KOLAnalystVerdict
from zetryn.core import END, Graph, RuleNode
from zetryn.llm import LLMClient, LLMNode

from ..kol_registry import KOLRegistry
from ..nodes import kol_nodes


def build_kol_copytrade(
    knowledge_pack=None,
    *,
    registry: KOLRegistry | None = None,
    mode: str = "rule",
    llm_client: LLMClient | None = None,
    model: str | None = None,
) -> Graph:
    """Build and compile the KOL copy-trade graph.

    Args:
        knowledge_pack: A `KnowledgePack` to derive a `KOLRegistry` from.
            Either this or `registry` is required.
        registry: Pre-built `KOLRegistry` (overrides any derived from
            `knowledge_pack` when both are given).
        mode: "rule" (default, no LLM) or "confirmed" (LLM analyst before
            sizing). "confirmed" requires `llm_client`.
        llm_client: Required when `mode="confirmed"`. Any `LLMClient`
            implementation, including `LLMRouter`.
        model: Optional model id override forwarded to the LLM client.

    If the pack contains no `kol_whitelist.json` namespace the resulting
    registry will be empty and every incoming event will be rejected
    with `action="skip"` and a clear reason. The graph still compiles
    and runs — graceful degradation, not a crash.
    """
    if mode not in ("rule", "confirmed"):
        raise ValueError(f"unsupported mode: {mode!r}. Use 'rule' or 'confirmed'.")
    if mode == "confirmed" and llm_client is None:
        raise ValueError("mode='confirmed' requires an llm_client")
    if registry is None:
        if knowledge_pack is None:
            raise ValueError(
                "build_kol_copytrade requires either knowledge_pack or registry"
            )
        registry = KOLRegistry.from_pack(knowledge_pack)

    g = Graph("kol_copytrade")
    g.add_node(RuleNode("fast_safety", kol_nodes.fast_safety))
    g.add_node(RuleNode("kol_quality", kol_nodes.make_kol_quality(registry)))
    g.add_node(RuleNode("fast_market", kol_nodes.fast_market))
    g.add_node(RuleNode("sizing", kol_nodes.sizing))

    if mode == "confirmed":
        g.add_node(
            LLMNode(
                "kol_analyst",
                llm_client,
                KOLAnalystVerdict,
                kol_nodes.kol_analyst_prompt,
                output_key="kol_analyst",
                fallback_fn=kol_nodes.neutral_kol_verdict,
                model=model,
            )
        )

    g.set_entry("fast_safety")
    g.add_edge("fast_safety", "kol_quality")
    g.add_edge("kol_quality", "fast_market")
    if mode == "confirmed":
        g.add_edge("fast_market", "kol_analyst")
        g.add_edge("kol_analyst", "sizing")
    else:
        g.add_edge("fast_market", "sizing")
    g.add_edge("sizing", END)
    return g.compile()
