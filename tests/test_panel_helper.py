"""Tests for the single_llm_specialist helper."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from zetryn.core.state import State
from zetryn.llm.types import LLMResult, Message
from zetryn.panel import PanelNode, single_llm_specialist


class DummyVerdict(BaseModel):
    score: float = 0.0
    note: str = ""


class _StubClient:
    """Returns a fixed JSON payload that validates against DummyVerdict."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    async def complete(self, messages, *, model=None, temperature=0.2, json_mode=False, tools=None):
        return LLMResult(text=self._payload, model="stub", latency_ms=0.0)


def _prompt(state: State) -> list[Message]:
    return [{"role": "user", "content": "x"}]


@pytest.mark.asyncio
async def test_single_llm_specialist_runs_standalone():
    client = _StubClient('{"score": 0.9, "note": "high"}')
    g = single_llm_specialist("safety", client, DummyVerdict, _prompt)
    final = await g.run(State())
    assert isinstance(final.output, DummyVerdict)
    assert final.output.score == 0.9
    assert final.output.note == "high"


@pytest.mark.asyncio
async def test_single_llm_specialist_inside_panel():
    client_a = _StubClient('{"score": 0.8}')
    client_b = _StubClient('{"score": 0.3}')

    panel = PanelNode(
        "panel",
        specialists={
            "a": single_llm_specialist("a_spec", client_a, DummyVerdict, _prompt),
            "b": single_llm_specialist("b_spec", client_b, DummyVerdict, _prompt),
        },
        aggregator=lambda results, state: {
            name: v.score for name, v in results.items()
        },
    )
    state = State()
    await panel.run(state)
    assert state.scratch["panel"] == {"a": 0.8, "b": 0.3}
