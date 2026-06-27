"""Example: Early-Stage Dip Buy agent (v0.15.0 / S6).

Offline by default (stub LLM). Set ``ZETRYN_DIP_USE_GROQ=1`` and provide
``GROQ_API_KEY`` in the environment to run with a real Groq client.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, build_dip_buy
from trading import DipBuyConfig, DipBuyContext, DipBuySnapshot
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message

_NOW = 1_751_000_000.0


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {
            "action": "buy",
            "size_pct": 0.55,
            "confidence": 0.72,
            "reasoning": "strong holder retention + buy-ratio recovery after the dump",
            "concerns": ["sell pressure still slightly elevated"],
        }
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self):
        pass


def _snap(event_type="launch", **over) -> DipBuySnapshot:
    base = dict(
        event_type=event_type,
        mint="So11111111111111111111111111111111111111112",
        detected_at_ts=_NOW,
        time_since_event_seconds=180.0,
        price_vs_ath_pct=-0.30,
        sell_pressure_score=0.20,
        buy_ratio_5m=0.60,
        holder_retention_pct=0.75,
        unique_buyers_trend=0.30,
        price_stable_seconds=60.0,
    )
    base.update(over)
    return DipBuySnapshot(**base)


CASES = [
    ("GOOD launch — rule (classic dip)", DipBuyConfig(decision_mode="rule"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("GOOD launch — llm mode", DipBuyConfig(decision_mode="llm"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("GOOD launch — hybrid_audit", DipBuyConfig(decision_mode="hybrid_audit"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("GOOD graduation — wider window (30min)", DipBuyConfig(
        event_type="graduation",
        max_time_since_event_seconds=1800.0,
        decision_mode="rule",
    ), _snap(event_type="graduation", time_since_event_seconds=900.0), SAMPLE_TOKENS["GOOD"]),
    ("SKIP — dump not settled (high sell pressure)", DipBuyConfig(), _snap(sell_pressure_score=0.80), SAMPLE_TOKENS["GOOD"]),
    ("SKIP — too early (20s)", DipBuyConfig(), _snap(time_since_event_seconds=20.0), SAMPLE_TOKENS["GOOD"]),
    ("SKIP — insufficient dip (5%)", DipBuyConfig(), _snap(price_vs_ath_pct=-0.05), SAMPLE_TOKENS["GOOD"]),
    ("ABORT — rug contract", DipBuyConfig(), _snap(), SAMPLE_TOKENS["RUG"]),
]


async def _run_case(label, cfg, snap, token, llm):
    g = build_dip_buy(llm_client=llm)
    state = await g.run(State(context=DipBuyContext(token=token, snapshot=snap, config=cfg)))
    d = state.output
    nodes = " → ".join(t.node for t in state.trace)
    flags = {k: v for k, v in d.flags.items() if v}
    print(f"\n{'─'*60}")
    print(f"Case : {label}")
    print(f"Mode : {cfg.decision_mode} | event: {snap.event_type}")
    print(f"Path : {nodes}")
    print(f"Action: {d.action}  size={d.size}  conf={d.confidence:.2f}")
    print(f"Flags : {flags or '—'}")
    for r in d.reasons:
        print(f"  • {r}")
    if cfg.decision_mode == "hybrid_audit" and "audit_task" in state.scratch:
        print("  [audit task dispatched — awaiting…]")
        try:
            audit = await asyncio.wait_for(state.scratch["audit_task"], timeout=5.0)
            print(f"  Audit: agrees={audit.agrees}  concerns={audit.concerns}")
        except TimeoutError:
            print("  Audit timed out")


async def main():
    use_groq = os.getenv("ZETRYN_DIP_USE_GROQ") == "1"

    if use_groq:
        from zetryn.llm import OpenAICompatibleClient, ProviderConfig
        llm = OpenAICompatibleClient(ProviderConfig(
            base_url="https://api.groq.com/openai/v1",
            key_envs=["GROQ_API_KEY"],
        ))
    else:
        llm = _StubLLM()

    print("Early-Stage Dip Buy — S6")
    for label, cfg, snap, token in CASES:
        await _run_case(label, cfg, snap, token, llm)

    if use_groq:
        await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
