"""Agent D — Pump.fun graduation snipe (v0.12.0).

When a Pump.fun token graduates from the bonding curve to Raydium, a short
entry window opens. The bot subscribes to graduation events outside the
framework, enriches the bought token's ``TokenInput``, fills a
``GraduationEvent``, and hands the framework a ``GraduationContext`` per
event. The framework returns a ``Decision``.

Modes (selected via ``GraduationConfig.decision_mode``):

  rule (default)
    fast_safety → graduation_gate → market_gate → rule_size_and_buy → END

  llm / hybrid
    fast_safety → graduation_gate → market_gate → [reflect?] → grad_decide → END
    ``hybrid`` adds a deterministic guardrail (forced abort on rug / LP not
    burned, hard size cap). When a ``decision_log`` is provided, a
    ``ReflectiveNode`` is inserted between ``market_gate`` and ``grad_decide``
    so the LLM sees a `lessons_text` block compiled from recent losers.

  hybrid_audit
    fast_safety → graduation_gate → market_gate → rule_size_and_buy →
        audit_dispatch → END
    Rule decides instantly (sub-ms), then fires an async LLM audit task the
    bot can ``await`` later. Reflection is intentionally skipped — the
    sub-ms sync path must not block on a memory read. The bot can reflect
    offline.
"""

from __future__ import annotations

from trading.schemas import GraduationVerdict
from zetryn.core import END, Graph, RuleNode
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, LLMDecisionNode
from zetryn.memory import DecisionLog, ReflectiveNode

from ..nodes import graduation_nodes as gn


def build_graduation(
    llm_client: LLMClient | None = None,
    *,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
    decision_log: DecisionLog | None = None,
    reflect_window: int = 20,
    reflect_feature_keys: list[str] | None = None,
    reflect_top_k: int = 5,
) -> Graph:
    """Build and compile the graduation snipe graph.

    Signature mirrors ``build_sniper`` / ``build_kol_copytrade`` for API
    consistency. If ``llm_client`` is None the graph stays pure-rule.
    """
    g = Graph("graduation_snipe")
    g.add_node(RuleNode("fast_safety", gn.fast_safety))
    g.add_node(RuleNode("graduation_gate", gn.graduation_gate))
    g.add_node(RuleNode("market_gate", gn.market_gate))
    g.add_node(RuleNode("rule_buy", gn.rule_size_and_buy))

    has_llm = llm_client is not None
    has_reflect = has_llm and decision_log is not None
    if has_llm:
        g.add_node(
            LLMDecisionNode(
                "grad_decide",
                llm_client,
                GraduationVerdict,
                gn.make_graduation_prompt(knowledge_pack),
                gn.graduation_result,
                guardrail_fn=gn.graduation_guardrail,
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
    g.add_edge("fast_safety", "graduation_gate")
    g.add_edge("graduation_gate", "market_gate")

    if has_llm:
        # rule + hybrid_audit go to rule_buy first (instant decision).
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
            g.add_edge("reflect", "grad_decide")
        else:
            g.add_edge(
                "market_gate",
                "grad_decide",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
        g.add_edge("grad_decide", END)
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
