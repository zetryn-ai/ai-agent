"""Example: how a bot calls the zetryn scanner.

Runs fully offline with a stub LLM so it needs no API key. To use a real free-tier
provider, swap ``_StubLLM()`` for an ``OpenAICompatibleClient`` (see comments).
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

# Make the repo-root `trading`/`strategies` packages importable when run as a script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from strategies import SAMPLE_TOKENS, build_scanner
from trading import ScannerConfig, TradingContext
from zetryn.core import State
from zetryn.llm.types import LLMResult, Message


class _StubLLM:
    async def complete(self, messages: list[Message], **kw) -> LLMResult:
        payload = {
            "score": 0.82,
            "sentiment": "bullish",
            "rug_signals": [],
            "reasoning": "active socials, coherent meme",
        }
        return LLMResult(text=json.dumps(payload), model="stub", latency_ms=1.0)

    async def aclose(self) -> None:
        pass


# --- Real provider (uncomment, set GROQ_API_KEY_1 in .env) -------------------
# from dotenv import load_dotenv
# from zetryn.llm import GROQ_BASE_URL, OpenAICompatibleClient, ProviderConfig
# load_dotenv()
# llm = OpenAICompatibleClient(ProviderConfig(
#     name="groq", base_url=GROQ_BASE_URL, model="llama-3.3-70b-versatile",
#     key_envs=["GROQ_API_KEY_1", "GROQ_API_KEY_2"]))


async def main() -> None:
    llm = _StubLLM()
    scanner = build_scanner(llm)

    for mint, token in SAMPLE_TOKENS.items():
        # In a real bot you'd build TokenInput from your data sources here.
        ctx = TradingContext(token=token, config=ScannerConfig())
        state = await scanner.run(State(context=ctx))
        d = state.output
        path = " -> ".join(t.node for t in state.trace)
        print(f"\n[{mint}] action={d.action.upper()} confidence={d.confidence}")
        print(f"  scores : {d.scores}")
        print(f"  reasons: {'; '.join(d.reasons)}")
        print(f"  path   : {path}")

    await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
