"""Agent F — Early-Stage Dip Buy (v0.15.0 / S6).

One agent, two events. After a Pump.fun token launches or graduates,
a dump wave follows. This agent waits for that dump to settle and
enters when sell pressure thins out, holders retain, and unique buyers
recover. The bot monitors the token's time-series, computes recovery
metrics, and pushes a ``DipBuyContext`` per candidate entry window.
The framework returns a ``Decision``.

Modes (selected via ``DipBuyConfig.decision_mode``):

  rule (default)
    fast_safety → timing_gate → dip_gate → recovery_gate →
        market_gate → rule_size_and_buy → END

  llm / hybrid
    fast_safety → timing_gate → dip_gate → recovery_gate →
        market_gate → [reflect?] → dip_decide → END
    ``hybrid`` adds a deterministic guardrail (forced abort on rug /
    size cap). When a ``decision_log`` is provided, a ``ReflectiveNode``
    is inserted before ``dip_decide`` so the LLM sees lessons from
    recent losing dip entries.

  hybrid_audit
    ... → rule_size_and_buy → audit_dispatch → END
    Rule decides instantly; async LLM audit fires in background.
"""

from __future__ import annotations

from trading.schemas import DipBuyVerdict
from zetryn.core import END, Graph, RuleNode
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, LLMDecisionNode
from zetryn.memory import DecisionLog, ReflectiveNode

from ..nodes import dip_buy_nodes as dn


def build_dip_buy(
    llm_client: LLMClient | None = None,
    *,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
    decision_log: DecisionLog | None = None,
    reflect_window: int = 20,
    reflect_feature_keys: list[str] | None = None,
    reflect_top_k: int = 5,
) -> Graph:
    """Build and compile the Early-Stage Dip Buy graph.

    Signature mirrors ``build_graduation`` / ``build_confluence`` for
    API consistency. If ``llm_client`` is None the graph stays pure-rule.
    """
    g = Graph("early_stage_dip_buy")
    g.add_node(RuleNode("fast_safety", dn.fast_safety))
    g.add_node(RuleNode("timing_gate", dn.timing_gate))
    g.add_node(RuleNode("dip_gate", dn.dip_gate))
    g.add_node(RuleNode("recovery_gate", dn.recovery_gate))
    g.add_node(RuleNode("market_gate", dn.market_gate))
    g.add_node(RuleNode("rule_buy", dn.rule_size_and_buy))

    has_llm = llm_client is not None
    has_reflect = has_llm and decision_log is not None

    if has_llm:
        g.add_node(
            LLMDecisionNode(
                "dip_decide",
                llm_client,
                DipBuyVerdict,
                dn.make_dip_prompt(knowledge_pack),
                dn.dip_result,
                guardrail_fn=dn.dip_guardrail,
                model=model,
            )
        )
        g.add_node(
            RuleNode(
                "audit_dispatch",
                dn.make_audit_dispatch(
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

    # Static edges shared by all modes
    g.set_entry("fast_safety")
    g.add_edge("fast_safety", "timing_gate")
    g.add_edge("timing_gate", "dip_gate")
    g.add_edge("dip_gate", "recovery_gate")
    g.add_edge("recovery_gate", "market_gate")

    if has_llm:
        g.add_edge(
            "market_gate",
            "rule_buy",
            when=lambda s: s.context.config.decision_mode in ("rule", "hybrid_audit"),
        )
        if has_reflect:
            g.add_edge(
                "market_gate",
                "reflect",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
            g.add_edge("reflect", "dip_decide")
        else:
            g.add_edge(
                "market_gate",
                "dip_decide",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
        g.add_edge("dip_decide", END)
        g.add_edge(
            "rule_buy",
            "audit_dispatch",
            when=lambda s: s.context.config.decision_mode == "hybrid_audit",
        )
        g.add_edge(
            "rule_buy",
            END,
            when=lambda s: s.context.config.decision_mode == "rule",
        )
        g.add_edge("audit_dispatch", END)
    else:
        g.add_edge("market_gate", "rule_buy")
        g.add_edge("rule_buy", END)

    return g.compile()
