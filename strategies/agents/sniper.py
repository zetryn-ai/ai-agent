"""Agent B — the auto-snipe agent.

Speed-first. Modes selected via ``SniperConfig.decision_mode``:

- **rule** (default): fast_safety -> fast_market -> rule_size_and_buy. Pure-rule,
  sub-millisecond, no LLM in the hot loop. ``fast_safety`` can abort instantly.
- **llm** / **hybrid**: same gates, then an ``LLMDecisionNode`` decides the entry.
  In hybrid mode a deterministic guardrail clamps/vetoes the LLM (forced abort on
  rug, hard size cap) — rules always win. When a ``DecisionLog`` is provided at
  build time, a ``ReflectiveNode`` is inserted between ``fast_market`` and
  ``snipe_decide`` so the LLM sees a lessons block compiled from recent losers.
- **hybrid_audit** (M9): rule decides instantly (sub-ms) AND an async LLM audit
  is dispatched as a background task. Decision is returned to the bot immediately;
  the audit task lands in ``state.scratch['audit_task']`` for the bot to ``await``
  and persist (e.g. to ``DecisionLog``). The trading hot path is never blocked.
  Reflection is intentionally skipped here — the whole point of this mode is
  the sub-ms rule path; reading ``DecisionLog`` synchronously would defeat it.
  The bot can run reflection in its own offline pipeline if desired.
"""

from __future__ import annotations

from zetryn.core import END, Graph, RuleNode
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, LLMDecisionNode
from zetryn.memory import DecisionLog, ReflectiveNode

from ..nodes import sniper_nodes as sn


def build_sniper(
    llm_client: LLMClient | None = None,
    *,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
    decision_log: DecisionLog | None = None,
    reflect_window: int = 20,
    reflect_feature_keys: list[str] | None = None,
    reflect_top_k: int = 5,
) -> Graph:
    """Build and compile the sniper graph.

    If ``llm_client`` is None (or config keeps decision_mode='rule'), the LLM nodes
    are not added and the graph stays a pure-rule fast path.

    Pass ``knowledge_pack`` to layer a deployment-specific playbook on top of
    both the snipe-decide prompt and the hybrid_audit prompt.

    Pass ``decision_log`` to enable the reflective loop for ``llm`` / ``hybrid``
    modes: a ``ReflectiveNode`` compiles a ``lessons_text`` summary from the last
    ``reflect_window`` decisions, ranked by loss patterns. The LLM analyst then
    sees that summary as an extra system block before deciding. Reflection is
    NOT wired into ``hybrid_audit`` — that mode's sub-ms rule path must not
    block on a memory read; the bot can reflect offline.
    """
    g = Graph("memecoin_sniper")
    g.add_node(RuleNode("fast_safety", sn.fast_safety))
    g.add_node(RuleNode("fast_market", sn.fast_market))
    g.add_node(RuleNode("rule_buy", sn.rule_size_and_buy))

    has_llm = llm_client is not None
    has_reflect = has_llm and decision_log is not None
    if has_llm:
        g.add_node(
            LLMDecisionNode(
                "snipe_decide",
                llm_client,
                sn.SnipeDecision,
                sn.make_snipe_prompt(knowledge_pack),
                sn.snipe_result,
                guardrail_fn=sn.snipe_guardrail,
                model=model,
            )
        )
        g.add_node(
            RuleNode(
                "audit_dispatch",
                sn.make_audit_dispatch(
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
    g.add_edge("fast_safety", "fast_market")

    if has_llm:
        # rule + hybrid_audit go to rule_buy first (instant decision)
        g.add_edge(
            "fast_market",
            "rule_buy",
            when=lambda s: s.context.config.decision_mode in ("rule", "hybrid_audit"),
        )
        if has_reflect:
            # llm / hybrid: detour through reflect before the LLM decides
            g.add_edge(
                "fast_market",
                "reflect",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
            g.add_edge("reflect", "snipe_decide")
        else:
            # llm / hybrid skip rule_buy and let the LLM decide directly
            g.add_edge(
                "fast_market",
                "snipe_decide",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
        g.add_edge("snipe_decide", END)
        # hybrid_audit: after instant rule decide, fire async audit
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
        g.add_edge("fast_market", "rule_buy")
        g.add_edge("rule_buy", END)

    return g.compile()
