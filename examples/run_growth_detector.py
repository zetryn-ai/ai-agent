"""Example: Organic Growth Detector agent (v0.16.0 / A1).

Offline by default (stub LLM). Set ``ZETRYN_GROWTH_USE_GROQ=1`` and provide
``GROQ_API_KEY`` in the environment to run with a real Groq client.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, build_organic_detector
from trading import GrowthConfig, GrowthContext, GrowthSnapshot
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message

_NOW = 1_751_000_000.0


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {
            "classification": "organic",
            "confidence": 0.78,
            "promote_scanner": True,
            "signals": ["steady_climb", "healthy_pullback", "rising_unique_buyers"],
            "reasoning": "consistent volume acceleration with real sell presence",
        }
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self):
        pass


def _snap(**over) -> GrowthSnapshot:
    base = dict(
        mint="So11111111111111111111111111111111111111112",
        detected_at_ts=_NOW,
        observation_seconds=300.0,
        candle_count=10,
        price_trajectory="steady_climb",
        sell_presence_pct=0.30,
        unique_buyer_trend=0.40,
        holder_growth_rate=3.0,
        has_healthy_pullback=True,
        max_drawdown_pct=0.12,
        whale_volume_pct=0.25,
        volume_acceleration=1.8,
    )
    base.update(over)
    return GrowthSnapshot(**base)


CASES = [
    ("ORGANIC — all 5 dims pass", GrowthConfig(decision_mode="rule"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("ORGANIC — rule mode (same, explicit)", GrowthConfig(decision_mode="rule"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("ORGANIC — llm mode", GrowthConfig(decision_mode="llm"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("ORGANIC — hybrid_audit", GrowthConfig(decision_mode="hybrid_audit"), _snap(), SAMPLE_TOKENS["GOOD"]),
    ("SUSPICIOUS — no pullback + weak buyers (4/5)", GrowthConfig(),
     _snap(has_healthy_pullback=False, unique_buyer_trend=-0.50), SAMPLE_TOKENS["GOOD"]),
    ("MANIPULATED — vertical pump + zero sells", GrowthConfig(),
     _snap(price_trajectory="vertical_pump", sell_presence_pct=0.005), SAMPLE_TOKENS["GOOD"]),
    ("MANIPULATED — extreme whale (92%)", GrowthConfig(),
     _snap(whale_volume_pct=0.92), SAMPLE_TOKENS["GOOD"]),
    ("SKIP — too short observation (30s)", GrowthConfig(),
     _snap(observation_seconds=30.0), SAMPLE_TOKENS["GOOD"]),
    ("ABORT — rug contract", GrowthConfig(), _snap(), SAMPLE_TOKENS["RUG"]),
]


async def _run_case(label, cfg, snap, token, llm):
    g = build_organic_detector(llm_client=llm)
    state = await g.run(State(context=GrowthContext(token=token, snapshot=snap, config=cfg)))
    d = state.output
    nodes = " → ".join(t.node for t in state.trace)
    flags = {k: v for k, v in d.flags.items() if v}
    print(f"\n{'─'*60}")
    print(f"Case  : {label}")
    print(f"Mode  : {cfg.decision_mode}")
    print(f"Path  : {nodes}")
    score = d.scores.get("organic_score")
    print(f"Action: {d.action}  score={score}  conf={d.confidence:.2f}")
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
    use_groq = os.getenv("ZETRYN_GROWTH_USE_GROQ") == "1"

    if use_groq:
        from zetryn.llm import OpenAICompatibleClient, ProviderConfig
        llm = OpenAICompatibleClient(ProviderConfig(
            base_url="https://api.groq.com/openai/v1",
            key_envs=["GROQ_API_KEY"],
        ))
    else:
        llm = _StubLLM()

    print("Organic Growth Detector — A1")
    for label, cfg, snap, token in CASES:
        await _run_case(label, cfg, snap, token, llm)

    if use_groq:
        await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
