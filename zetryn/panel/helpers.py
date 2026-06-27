"""Helpers for building common specialist shapes.

The panel API expects each specialist to be a full :class:`Graph`. For the
common case "specialist is one LLM call", :func:`single_llm_specialist`
builds a 1-node Graph in one line so the user doesn't have to.
"""

from __future__ import annotations


from pydantic import BaseModel

from ..core.graph import Graph
from ..core.node import RuleNode
from ..core.state import Command, State
from ..llm.client import LLMClient
from ..llm.node import FallbackFn, LLMNode, PromptFn


def single_llm_specialist(
    name: str,
    client: LLMClient,
    schema: type[BaseModel],
    prompt_fn: PromptFn,
    *,
    output_key: str | None = None,
    fallback_fn: FallbackFn | None = None,
    model: str | None = None,
    max_attempts: int = 3,
) -> Graph:
    """Build a one-node Graph that wraps a single :class:`LLMNode`.

    The wrapped LLMNode writes its validated result to
    ``state.scratch[output_key or name]``. A trailing rule node copies that
    value into ``state.output`` so the panel sees it via ``final.output``
    (matching every other specialist shape).
    """
    key = output_key or name
    llm_node = LLMNode(
        name=f"{name}__llm",
        client=client,
        schema=schema,
        prompt_fn=prompt_fn,
        output_key=key,
        fallback_fn=fallback_fn,
        model=model,
        max_attempts=max_attempts,
    )

    def _emit_output(state: State) -> Command | None:
        state.output = state.scratch.get(key)
        return None

    finalize = RuleNode(f"{name}__finalize", _emit_output)

    g = Graph(name)
    g.add_node(llm_node)
    g.add_node(finalize)
    g.add_edge(llm_node.name, finalize.name)
    g.set_entry(llm_node.name)
    g.compile()
    return g
