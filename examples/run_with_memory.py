"""Example: scanner + observability (logging hooks) + memory (blacklist, decision log).

Shows how a bot wires the M4 pieces around the framework. Runs offline (stub LLM).
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, build_scanner
from trading import ScannerConfig, TradingContext
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message
from zetryn.memory import Blacklist, DecisionLog, InMemoryStore
from zetryn.observability import logging_hooks, run_summary


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {"score": 0.8, "sentiment": "bullish", "rug_signals": [], "reasoning": "ok"}
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


async def main() -> None:
    scanner = build_scanner(_StubLLM())
    store = InMemoryStore()
    blacklist = Blacklist(store)
    decisions = DecisionLog(store)
    hooks = logging_hooks()  # structured JSON to stderr

    for mint, token in SAMPLE_TOKENS.items():
        if await blacklist.is_blacklisted(mint):
            print(f"[{mint}] skipped (blacklisted)")
            continue

        ctx = TradingContext(token=token, config=ScannerConfig())
        state = await scanner.run(State(context=ctx), hooks=hooks)
        d = state.output

        await decisions.log(state.run_id, {"mint": mint, **d.model_dump()})
        if d.flags.get("rug_risk"):
            await blacklist.add(mint, "rug risk detected")

        path = run_summary(state)["path"]
        print(f"\n[{mint}] {d.action.upper()} ({d.confidence}) | path={path}")

    print("\n--- decision log stats ---")
    print(json.dumps(await decisions.stats(), indent=2))
    print("--- blacklist ---")
    print([b["key"] for b in await blacklist.all()])


if __name__ == "__main__":
    asyncio.run(main())
