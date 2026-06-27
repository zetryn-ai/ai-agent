"""Example: Smart Money Confluence agent (v0.14.0 / S5).

Offline by default (stub LLM). Set ``ZETRYN_CONFLUENCE_USE_GROQ=1`` and
provide ``GROQ_API_KEY`` in the environment to run with a real Groq client.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, SmartWalletRegistry, build_confluence
from trading import (
    ConfluenceConfig,
    ConfluenceContext,
    ConfluenceEvent,
    SmartWalletAccumulation,
    SmartWalletProfile,
)
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message

_NOW = 1_751_000_000.0


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {
            "action": "buy",
            "size_pct": 0.6,
            "confidence": 0.78,
            "reasoning": "7 smart wallets converged in 4h — strong thesis",
            "concerns": ["moderate top10 concentration"],
        }
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self):
        pass


def _build_registry() -> SmartWalletRegistry:
    wallets = {
        "wallet_A": SmartWalletProfile(hit_rate=0.65, avg_pnl_pct=1.8, trades_30d=60, tier="S"),
        "wallet_B": SmartWalletProfile(hit_rate=0.58, avg_pnl_pct=1.2, trades_30d=45, tier="A"),
        "wallet_C": SmartWalletProfile(hit_rate=0.52, avg_pnl_pct=0.9, trades_30d=35, tier="A"),
        "wallet_D": SmartWalletProfile(hit_rate=0.47, avg_pnl_pct=0.7, trades_30d=28, tier="B"),
        "wallet_E": SmartWalletProfile(hit_rate=0.42, avg_pnl_pct=0.5, trades_30d=22, tier="B"),
        "wallet_F": SmartWalletProfile(hit_rate=0.40, avg_pnl_pct=0.4, trades_30d=18, tier="B"),
        "wallet_G": SmartWalletProfile(hit_rate=0.38, avg_pnl_pct=0.3, trades_30d=15, tier="B"),
    }
    return SmartWalletRegistry(wallets, min_tier="B", min_hit_rate=0.35)


def _build_event() -> ConfluenceEvent:
    wallets = ["wallet_A", "wallet_B", "wallet_C", "wallet_D", "wallet_E", "wallet_F", "wallet_G"]
    return ConfluenceEvent(
        mint="So11111111111111111111111111111111111111112",
        detected_at_ts=_NOW,
        window_seconds=4 * 3600,  # 4-hour rolling window
        accumulations=[
            SmartWalletAccumulation(
                wallet=w,
                mint="So11111111111111111111111111111111111111112",
                sol_amount=2.0 if w in ("wallet_A", "wallet_B") else 1.0,
                detected_at_ts=_NOW - i * 300,  # staggered over time
                block_age_seconds=float(i * 5),
            )
            for i, w in enumerate(wallets)
        ],
    )


CASES = [
    ("GOOD — rule mode", ConfluenceConfig(decision_mode="rule"), SAMPLE_TOKENS["GOOD"]),
    ("GOOD — llm mode", ConfluenceConfig(decision_mode="llm"), SAMPLE_TOKENS["GOOD"]),
    ("GOOD — hybrid_audit mode", ConfluenceConfig(decision_mode="hybrid_audit"), SAMPLE_TOKENS["GOOD"]),
    ("RUG — rule mode", ConfluenceConfig(decision_mode="rule"), SAMPLE_TOKENS["RUG"]),
    ("THIN — rule mode", ConfluenceConfig(decision_mode="rule"), SAMPLE_TOKENS["THIN"]),
]


async def _run_case(label: str, cfg: ConfluenceConfig, token, registry, event, llm):
    g = build_confluence(llm_client=llm, registry=registry)
    state = await g.run(State(context=ConfluenceContext(token=token, event=event, config=cfg)))
    d = state.output
    nodes = " → ".join(t.node for t in state.trace)
    flags = {k: v for k, v in d.flags.items() if v}
    print(f"\n{'─'*60}")
    print(f"Case : {label}")
    print(f"Mode : {cfg.decision_mode}")
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
            print("  Audit timed out (stub should not happen — check stub LLM)")


async def main():
    use_groq = os.getenv("ZETRYN_CONFLUENCE_USE_GROQ") == "1"

    if use_groq:
        from zetryn.llm import OpenAICompatibleClient, ProviderConfig
        llm = OpenAICompatibleClient(ProviderConfig(
            base_url="https://api.groq.com/openai/v1",
            key_envs=["GROQ_API_KEY"],
        ))
    else:
        llm = _StubLLM()

    registry = _build_registry()
    event = _build_event()

    print(f"Smart Money Confluence — {len(registry)} wallets, {len(event.accumulations)} accumulations")
    print(f"Window: {event.window_seconds/3600:.1f}h | Token: {event.mint[:8]}…")

    for label, cfg, token in CASES:
        await _run_case(label, cfg, token, registry, event, llm)

    if use_groq:
        await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
