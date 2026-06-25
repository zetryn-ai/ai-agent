"""Agent C — KOL Copy-Trade (v0.6.0, `rule` mode).

Pure-rule fast path that consumes a `KOLContext` and emits a `Decision`.
The bot subscribes to KOL wallet events outside the framework, enriches
the bought token's `TokenInput`, and hands the framework a `KOLContext`
per event. The framework decides whether to copy and at what size.

Flow:

    fast_safety   -> kol_quality -> fast_market -> sizing -> END
         |              |               |
         '--------------'---------------'-> any rejection ends the run
                                            with action="skip"/"abort"

Boundary recap (see docs/plans/2026-06-25-kol-copytrade-strategy.md §0.5):
the framework defines + decides; the bot fetches and executes. The KOL
whitelist is loaded by the bot into a `KnowledgePack` and wrapped in
`KOLRegistry`, which this builder accepts. Cool-down state is also
bot-owned (passed in via `KOLContext.last_copy_ts`).

`confirmed` / `audit` modes (LLM tool-use + async second opinion) are
NOT in this release; they ship in v0.7.0+.
"""

from __future__ import annotations

from zetryn.core import END, Graph, RuleNode

from ..kol_registry import KOLRegistry
from ..nodes import kol_nodes


def build_kol_copytrade(knowledge_pack=None, *, registry: KOLRegistry | None = None) -> Graph:
    """Build and compile the rule-mode KOL copy-trade graph.

    Pass either a `knowledge_pack` (the function will derive a
    `KOLRegistry` from it via `KOLRegistry.from_pack(pack)`) or a
    pre-built `registry`. At least one is required; if both are given,
    `registry` wins.

    If the pack contains no `kol_whitelist.json` namespace the resulting
    registry will be empty and every incoming event will be rejected
    with `action="skip"` and a clear reason. The graph still compiles
    and runs — graceful degradation, not a crash.
    """
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

    g.set_entry("fast_safety")
    g.add_edge("fast_safety", "kol_quality")
    g.add_edge("kol_quality", "fast_market")
    g.add_edge("fast_market", "sizing")
    g.add_edge("sizing", END)
    return g.compile()
