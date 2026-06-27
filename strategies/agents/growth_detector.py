"""Agent G — Organic Growth Detector (v0.16.0 / A1).

Triage filter — classifies a token's post-launch time-series as organic,
suspicious, or manipulated. Returns a ``Decision`` with:

  action="buy"   (organic)    → bot promotes scanner candidate
  action="skip"  (suspicious) → bot runs normal scanner flow
  action="abort" (manipulated)→ bot skips and cools down the token

``Decision.flags["classification"]`` carries the string label.
``Decision.scores["organic_score"]`` carries the raw score for calibration.

Modes (selected via ``GrowthConfig.decision_mode``):

  rule (default)
    fast_safety → observation_gate → manipulation_gate →
        organic_classify → END

  llm / hybrid
    fast_safety → observation_gate → manipulation_gate →
        [reflect?] → growth_llm → END
    ``hybrid`` adds a guardrail that can only demote (organic → suspicious),
    never promote. Vertical pump + zero-sell always abort, even if LLM says
    organic.

  hybrid_audit
    ... → organic_classify → audit_dispatch → END
    Rule classifies instantly; async LLM audit fires in background.
    Unlike entry agents, audit_dispatch fires for ALL classifications
    (not just buys) — demotions are equally worth auditing.
"""

from __future__ import annotations

from trading.schemas import GrowthVerdict
from zetryn.core import END, Graph, RuleNode
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, LLMDecisionNode
from zetryn.memory import DecisionLog, ReflectiveNode

from ..nodes import growth_nodes as gn


def build_organic_detector(
    llm_client: LLMClient | None = None,
    *,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
    decision_log: DecisionLog | None = None,
    reflect_window: int = 20,
    reflect_feature_keys: list[str] | None = None,
    reflect_top_k: int = 5,
) -> Graph:
    """Build and compile the Organic Growth Detector graph.

    Signature mirrors other entry agents for API consistency.
    If ``llm_client`` is None the graph stays pure-rule.
    """
    g = Graph("organic_growth_detector")
    g.add_node(RuleNode("fast_safety", gn.fast_safety))
    g.add_node(RuleNode("observation_gate", gn.observation_gate))
    g.add_node(RuleNode("manipulation_gate", gn.manipulation_gate))
    g.add_node(RuleNode("organic_classify", gn.organic_classify))

    has_llm = llm_client is not None
    has_reflect = has_llm and decision_log is not None

    if has_llm:
        g.add_node(
            LLMDecisionNode(
                "growth_llm",
                llm_client,
                GrowthVerdict,
                gn.make_growth_prompt(knowledge_pack),
                gn.growth_result,
                guardrail_fn=gn.growth_guardrail,
                model=model,
            )
        )
        g.add_node(
            RuleNode(
                "audit_dispatch",
                gn.make_audit_dispatch(
                    llm_client, model=model, knowledge_pack=knowledge_pack
                ),
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

    g.set_entry("fast_safety")
    g.add_edge("fast_safety", "observation_gate")
    g.add_edge("observation_gate", "manipulation_gate")

    if has_llm:
        g.add_edge(
            "manipulation_gate",
            "organic_classify",
            when=lambda s: s.context.config.decision_mode in ("rule", "hybrid_audit"),
        )
        if has_reflect:
            g.add_edge(
                "manipulation_gate",
                "reflect",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
            g.add_edge("reflect", "growth_llm")
        else:
            g.add_edge(
                "manipulation_gate",
                "growth_llm",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
        g.add_edge("growth_llm", END)
        g.add_edge(
            "organic_classify",
            "audit_dispatch",
            when=lambda s: s.context.config.decision_mode == "hybrid_audit",
        )
        g.add_edge(
            "organic_classify",
            END,
            when=lambda s: s.context.config.decision_mode == "rule",
        )
        g.add_edge("audit_dispatch", END)
    else:
        g.add_edge("manipulation_gate", "organic_classify")
        g.add_edge("organic_classify", END)

    return g.compile()
