"""Example: Pump.fun graduation snipe agent (v0.12.0).

Offline by default (stub LLM). Set ``ZETRYN_GRAD_USE_GROQ=1`` and provide
``GROQ_API_KEY`` in the environment to run with a real Groq client.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, build_graduation
from trading import GraduationConfig, GraduationContext, GraduationEvent
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {
            "action": "buy",
            "size_pct": 0.6,
            "confidence": 0.75,
            "reasoning": "strong fill + organic buyers",
            "concerns": [],
        }
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


def _make_event(mint: str, **over) -> GraduationEvent:
    base = dict(
        mint=mint,
        pair_address=f"PAIR_{mint}",
        detected_at_ts=1_700_000_000.0,
        pair_age_seconds=2.5,
        bonding_curve_fill_seconds=180.0,
        bonding_curve_unique_buyers=140,
        bonding_curve_sol_raised=85.0,
        bonding_curve_premium_pct=6.0,
        initial_liquidity_sol=42.0,
        initial_liquidity_token_pct=20.0,
        lp_burned=True,
    )
    base.update(over)
    return GraduationEvent(**base)


def _llm_client():
    """Choose between the offline stub and a real Groq client via env flag."""
    if os.environ.get("ZETRYN_GRAD_USE_GROQ") != "1":
        return _StubLLM()
    from zetryn.llm import KeyPool, OpenAICompatibleClient, ProviderConfig

    cfg = ProviderConfig(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.1-70b-versatile",
        key_envs=["GROQ_API_KEY"],
    )
    return OpenAICompatibleClient(cfg, KeyPool.from_env(cfg.key_envs))


async def main() -> None:
    print("=== Pure-rule graduation snipe ===")
    rule_agent = build_graduation(llm_client=None)
    for mint in SAMPLE_TOKENS:
        ctx = GraduationContext(
            token=SAMPLE_TOKENS[mint],
            event=_make_event(mint),
            config=GraduationConfig(),
        )
        state = await rule_agent.run(State(context=ctx))
        d = state.output
        path = " -> ".join(t.node for t in state.trace)
        print(
            f"  {mint:8} {d.action.upper():6} size={d.size} | {path} | "
            f"{d.meta['latency_ms']}ms"
        )

    print("\n=== Hybrid (LLM decides, rules guardrail) ===")
    hybrid = build_graduation(_llm_client())
    cfg = GraduationConfig(decision_mode="hybrid", max_size=2.0)
    for mint in SAMPLE_TOKENS:
        ctx = GraduationContext(
            token=SAMPLE_TOKENS[mint],
            event=_make_event(mint),
            config=cfg,
        )
        state = await hybrid.run(State(context=ctx))
        d = state.output
        reasons = "; ".join(d.reasons)
        print(
            f"  {mint:8} {d.action.upper():6} size={d.size} conf={d.confidence} "
            f"| {reasons}"
        )


if __name__ == "__main__":
    asyncio.run(main())
