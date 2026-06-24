"""Example: the auto-snipe agent in pure-rule (fast) vs LLM/hybrid mode.

Shows the sub-second pure-rule path and the optional LLM-decided entry with a
deterministic guardrail. Runs offline (stub LLM).
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, build_sniper
from trading import SniperConfig, TradingContext
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {
            "action": "buy",
            "size_pct": 0.6,
            "confidence": 0.75,
            "reasoning": "momentum + KOL",
        }
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


async def main() -> None:
    print("=== Pure-rule fast path (no LLM) ===")
    rule_sniper = build_sniper(llm_client=None)
    for mint in SAMPLE_TOKENS:
        ctx = TradingContext(token=SAMPLE_TOKENS[mint], config=SniperConfig())
        state = await rule_sniper.run(State(context=ctx))
        d = state.output
        path = " -> ".join(t.node for t in state.trace)
        print(f"  {mint:8} {d.action.upper():6} size={d.size} | {path} | {d.meta['latency_ms']}ms")

    print("\n=== Hybrid (LLM decides, rules guardrail) ===")
    hybrid = build_sniper(_StubLLM())
    cfg = SniperConfig(use_llm=True, decision_mode="hybrid", max_size=4.0)
    for mint in SAMPLE_TOKENS:
        ctx = TradingContext(token=SAMPLE_TOKENS[mint], config=cfg)
        state = await hybrid.run(State(context=ctx))
        d = state.output
        reasons = "; ".join(d.reasons)
        print(f"  {mint:8} {d.action.upper():6} size={d.size} conf={d.confidence} | {reasons}")


if __name__ == "__main__":
    asyncio.run(main())
