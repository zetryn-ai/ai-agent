"""Example: LLM-driven tool-use loop wired into an analyst-style decision.

Demonstrates `ToolUseNode` — the analyst sees a token fact sheet plus two
callable tools, decides on its own when to invoke them, then returns a
structured verdict.

This is a standalone example (not the full scanner graph) so the tool
flow is easy to read. The same pattern can be dropped into any agent
graph that needs the analyst to gather more data mid-decision.

Runs with a stub LLM that scripts a realistic tool-use conversation so
no API key is required.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

from pydantic import BaseModel, Field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from zetryn.core import State
from zetryn.llm import ToolUseNode
from zetryn.llm.types import LLMResult, Message
from zetryn.tools import Tool, ToolRegistry

# -- Tools the analyst can invoke ------------------------------------------


async def check_rug(mint: str) -> dict:
    """Pretend RugCheck lookup. In production this would be a real API call."""
    return {"mint": mint, "safe": True, "score": 0.85, "issues": []}


async def get_smart_money_buys(mint: str, window_minutes: int = 5) -> dict:
    """Pretend smart-money tracker. Returns count of profitable wallets buying."""
    return {"mint": mint, "window_minutes": window_minutes, "smart_wallet_buys": 4}


class CheckRugInput(BaseModel):
    mint: str = Field(description="Token mint address")


class SmartMoneyInput(BaseModel):
    mint: str = Field(description="Token mint address")
    window_minutes: int = Field(default=5, ge=1, le=60)


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("check_rug", "Verify if a mint is a rug via on-chain analysis",
                      check_rug, input_schema=CheckRugInput))
    reg.register(Tool("get_smart_money_buys",
                      "Count smart-money wallet buys in a recent window",
                      get_smart_money_buys, input_schema=SmartMoneyInput))
    return reg


# -- Output schema the analyst must return after using tools --------------


class AnalystVerdict(BaseModel):
    action: str = Field(description="alert | watch | skip")
    confidence: float = Field(ge=0, le=1)
    reasoning: str


# -- Stub LLM that scripts a tool-use conversation ------------------------


class _ScriptedToolUseLLM:
    """3-turn scripted conversation: call rug check → call smart money → emit verdict."""

    def __init__(self) -> None:
        self.turn = 0
        self.specs_seen_each_call = 0

    async def complete(
        self,
        messages: list[Message],
        *,
        model=None,
        temperature=None,
        json_mode=False,
        tools=None,
    ) -> LLMResult:
        self.turn += 1
        self.specs_seen_each_call = len(tools or [])
        if self.turn == 1:
            return LLMResult(
                text="",
                model="stub",
                latency_ms=1.0,
                tool_calls=[{
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "check_rug",
                        "arguments": json.dumps({"mint": "GOOD_MINT"}),
                    },
                }],
            )
        if self.turn == 2:
            return LLMResult(
                text="",
                model="stub",
                latency_ms=1.0,
                tool_calls=[{
                    "id": "c2",
                    "type": "function",
                    "function": {
                        "name": "get_smart_money_buys",
                        "arguments": json.dumps({"mint": "GOOD_MINT", "window_minutes": 5}),
                    },
                }],
            )
        verdict = json.dumps({
            "action": "alert",
            "confidence": 0.82,
            "reasoning": (
                "Rug check clean (score 0.85). Smart money buys = 4 in 5 minutes — "
                "strong on-chain confluence. Recommending ALERT."
            ),
        })
        return LLMResult(text=verdict, model="stub", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


# -- Run --------------------------------------------------------------------


async def main() -> int:
    llm = _ScriptedToolUseLLM()
    reg = _registry()

    def prompt(state: State) -> list[Message]:
        return [
            {"role": "system", "content": (
                "You are a memecoin analyst. Use the available tools to gather "
                "evidence, then return a JSON verdict matching the schema "
                "{action: alert|watch|skip, confidence: 0..1, reasoning: str}."
            )},
            {"role": "user", "content": (
                "Token GOOD_MINT just appeared. Decide alert/watch/skip after "
                "checking the rug status and smart-money activity."
            )},
        ]

    node = ToolUseNode(
        "analyst", llm, reg,
        prompt_fn=prompt,
        schema=AnalystVerdict,
        max_iterations=6,
    )

    state = State()
    await node.run(state)

    verdict: AnalystVerdict = state.scratch["analyst"]
    trace = state.scratch["analyst__trace"]

    print(f"verdict.action     : {verdict.action.upper()}")
    print(f"verdict.confidence : {verdict.confidence:.2f}")
    print(f"verdict.reasoning  : {verdict.reasoning}\n")

    print(f"loop iterations    : {trace.iterations}")
    print(f"tools called       : {len(trace.tool_calls)}")
    for call in trace.tool_calls:
        fn = call.get("function", {})
        print(f"  - {fn.get('name')}({fn.get('arguments')})")
    print(f"truncated          : {trace.truncated}")
    print(f"tool specs per call: {llm.specs_seen_each_call} "
          f"(both registered tools visible to the model each turn)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
