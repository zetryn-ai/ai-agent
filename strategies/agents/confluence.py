"""Agent E — Smart Money Confluence (v0.14.0 / S5).

Fires when ≥ N pre-vetted smart wallets have accumulated the same token
within a rolling window. The bot subscribes to wallet feeds (Cielo, GMGN,
Helius), aggregates per-mint accumulations, fills a ``ConfluenceEvent``,
and hands the framework a ``ConfluenceContext`` per signal. The framework
returns a ``Decision``.

Modes (selected via ``ConfluenceConfig.decision_mode``):

  rule (default)
    fast_safety → confluence_gate → market_gate → rule_size_and_buy → END

  llm / hybrid
    fast_safety → confluence_gate → market_gate → [reflect?] →
        confluence_decide → END
    ``hybrid`` adds a deterministic guardrail (forced abort on rug / size
    cap). When a ``decision_log`` is provided, a ``ReflectiveNode`` is
    inserted so the LLM sees a ``lessons_text`` block from recent losers.

  hybrid_audit
    fast_safety → confluence_gate → market_gate → rule_size_and_buy →
        audit_dispatch → END
    Rule decides instantly (sub-ms), then fires an async LLM audit task
    the bot can ``await`` later. Reflection intentionally skipped on the
    fast path.

``registry`` parameter is optional. When provided, each wallet in the
``ConfluenceEvent`` is checked against the ``SmartWalletRegistry``
whitelist. When omitted, the gate falls back to ``ConfluenceConfig``
per-wallet floors only (no whitelist lookup).
"""

from __future__ import annotations

from trading.schemas import ConfluenceVerdict
from zetryn.core import END, Graph, RuleNode
from zetryn.knowledge import KnowledgePack
from zetryn.llm import LLMClient, LLMDecisionNode
from zetryn.memory import DecisionLog, ReflectiveNode

from ..nodes import confluence_nodes as cn
from ..smart_wallet_registry import SmartWalletRegistry


def build_confluence(
    llm_client: LLMClient | None = None,
    *,
    registry: SmartWalletRegistry | None = None,
    model: str | None = None,
    knowledge_pack: KnowledgePack | None = None,
    decision_log: DecisionLog | None = None,
    reflect_window: int = 20,
    reflect_feature_keys: list[str] | None = None,
    reflect_top_k: int = 5,
) -> Graph:
    """Build and compile the Smart Money Confluence graph.

    Signature mirrors ``build_graduation`` / ``build_kol_copytrade`` for
    API consistency. If ``llm_client`` is None the graph stays pure-rule.
    If ``registry`` is None, wallet quality falls back to
    ``ConfluenceConfig`` floors only.
    """
    g = Graph("smart_money_confluence")
    g.add_node(RuleNode("fast_safety", cn.fast_safety))
    g.add_node(RuleNode("confluence_gate", cn.make_confluence_gate(registry)))
    g.add_node(RuleNode("market_gate", cn.market_gate))
    g.add_node(RuleNode("rule_buy", cn.rule_size_and_buy))

    has_llm = llm_client is not None
    has_reflect = has_llm and decision_log is not None

    if has_llm:
        g.add_node(
            LLMDecisionNode(
                "confluence_decide",
                llm_client,
                ConfluenceVerdict,
                cn.make_confluence_prompt(knowledge_pack),
                cn.confluence_result,
                guardrail_fn=cn.confluence_guardrail,
                model=model,
            )
        )
        g.add_node(
            RuleNode(
                "audit_dispatch",
                cn.make_audit_dispatch(
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
    g.add_edge("fast_safety", "confluence_gate")
    g.add_edge("confluence_gate", "market_gate")

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
            g.add_edge("reflect", "confluence_decide")
        else:
            g.add_edge(
                "market_gate",
                "confluence_decide",
                when=lambda s: s.context.config.decision_mode in ("llm", "hybrid"),
            )
        g.add_edge("confluence_decide", END)
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
