"""Multi-agent panel — run multiple specialist sub-graphs and merge verdicts.

Rule-based orchestrator (no LLM-as-orchestrator): execution order, parallelism,
short-circuit, and aggregation are all defined by user-supplied Python. The
framework stays a transparent computation engine.

Two node types mirror the existing LLM pair:

- :class:`PanelNode` — intermediate panel; aggregator result → ``scratch``.
- :class:`PanelDecisionNode` — terminal panel; aggregator result → ``state.output``.

A :func:`single_llm_specialist` helper builds a one-node Graph for the
common case of "specialist = wrap one LLMNode".
"""

from .helpers import single_llm_specialist
from .panel import (
    Aggregator,
    PanelDecisionNode,
    PanelExecutionError,
    PanelNode,
    ShortCircuitFn,
)

__all__ = [
    "Aggregator",
    "PanelDecisionNode",
    "PanelExecutionError",
    "PanelNode",
    "ShortCircuitFn",
    "single_llm_specialist",
]
