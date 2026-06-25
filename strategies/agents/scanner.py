"""Agent A — the memecoin scanner + scorer (M8 AI-first).

Flow (M8 pivot to AI-first):

    safety_gate -> intel_gate -> market_gate -> [reflect?] -> analyst (LLM)
         |             |              |                              |
         '-------------'--------------'-> reject -> END               v
                                                                   finalize -> END

The three hard gates run first: instant abort for obvious rug / bundle / dead
tokens. They never consume an LLM call. Survivors optionally pass through a
``ReflectiveNode`` (when a ``DecisionLog`` is provided) that compiles recent
losers into a ``lessons_text`` block injected into the analyst prompt — closing
the learning loop. Then the analyst makes a single rich LLM call returning a
structured ``FullAnalysis``. ``finalize`` applies guardrails (can downgrade the
LLM's recommendation when it clashes with hard reality) and assembles the
``Decision``.

For backwards-compat / offline tests, ``llm_client=None`` is still accepted —
the graph then skips the analyst and ``finalize`` produces a neutral "watch"
Decision based on the rule scores already in scratch. Production usage MUST
provide an LLM client.
"""

from __future__ import annotations

from trading.schemas import FullAnalysis
from zetryn.core import END, Graph, RuleNode
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, LLMNode
from zetryn.memory import DecisionLog, ReflectiveNode

from ..nodes import decide, filters
from ..nodes.analyst import make_analyst_prompt, neutral_analysis


def build_scanner(
    llm_client: LLMClient | None = None,
    *,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
    decision_log: DecisionLog | None = None,
    reflect_window: int = 20,
    reflect_feature_keys: list[str] | None = None,
    reflect_top_k: int = 5,
) -> Graph:
    """Build and compile the AI-first scanner graph.

    With an LLM client the flow is: 3 hard gates -> [reflect?] -> analyst -> finalize.
    Without an LLM client the analyst (and reflect) are omitted and ``finalize``
    falls back to a rule-only neutral decision (kept for offline tests).

    Pass ``knowledge_pack`` to layer a deployment-specific playbook on top of
    the analyst's default system prompt. Markdown files under ``<pack>/system/``
    are injected as system messages (filename order) before the analyst's own
    instructions.

    Pass ``decision_log`` to enable the reflective loop: a `ReflectiveNode`
    summarises the last ``reflect_window`` decisions, ranks loss patterns by
    feature buckets, and the analyst sees that summary in its system prompt.
    The node is inserted between ``market_gate`` and ``analyst`` so it only
    runs on candidates that survive the hard gates — losers in the gate path
    don't waste a memory read.
    """
    g = Graph("memecoin_scanner")
    g.add_node(RuleNode("safety_gate", filters.safety_gate))
    g.add_node(RuleNode("intel_gate", filters.intel_gate))
    g.add_node(RuleNode("market_gate", filters.market_gate))
    g.add_node(RuleNode("finalize", decide.finalize))
    g.add_node(RuleNode("reject", decide.reject))

    has_llm = llm_client is not None
    has_reflect = has_llm and decision_log is not None

    if has_llm:
        g.add_node(
            LLMNode(
                "analyst",
                llm_client,
                FullAnalysis,
                make_analyst_prompt(knowledge_pack),
                output_key="analysis",
                fallback_fn=neutral_analysis,
                model=model,
            )
        )

    if has_reflect:
        g.add_node(
            ReflectiveNode(
                "reflect",
                decision_log,
                window=reflect_window,
                feature_keys=reflect_feature_keys,
                top_k=reflect_top_k,
            )
        )

    g.set_entry("safety_gate")

    g.add_edge("safety_gate", "reject", when=lambda s: not s.scratch["safety_ok"])
    g.add_edge("safety_gate", "intel_gate", when=lambda s: s.scratch["safety_ok"])
    g.add_edge("intel_gate", "reject", when=lambda s: not s.scratch["intel_ok"])
    g.add_edge("intel_gate", "market_gate", when=lambda s: s.scratch["intel_ok"])
    g.add_edge("market_gate", "reject", when=lambda s: not s.scratch["market_ok"])

    if has_reflect:
        g.add_edge("market_gate", "reflect", when=lambda s: s.scratch["market_ok"])
        g.add_edge("reflect", "analyst")
        g.add_edge("analyst", "finalize")
    elif has_llm:
        g.add_edge("market_gate", "analyst", when=lambda s: s.scratch["market_ok"])
        g.add_edge("analyst", "finalize")
    else:
        g.add_edge("market_gate", "finalize", when=lambda s: s.scratch["market_ok"])

    g.add_edge("finalize", END)
    g.add_edge("reject", END)
    return g.compile()
