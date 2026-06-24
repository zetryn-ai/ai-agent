"""The graph engine: compile nodes + edges into a runnable agent.

Routing rule: if a node returns a ``Command`` with ``goto`` set, that wins;
otherwise the engine follows the first matching declared edge. If neither applies,
the run terminates.

A validator runs at compile time to catch structural errors (missing entry, edges
to unknown nodes) before any money moves. Reachability issues are warnings, not
errors, because nodes may be reached dynamically via ``Command.goto``.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from .edge import Condition, Edge
from .hooks import Hooks, safe_fire
from .node import Node
from .state import END, Command, State, StepTrace


class GraphValidationError(Exception):
    """Raised at compile time when the graph is structurally invalid."""


class GraphExecutionError(Exception):
    """Raised at run time when a node fails or a loop bound is exceeded."""


class Graph:
    """A directed graph of nodes that runs to produce a final ``State``."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._edges_from: dict[str, list[Edge]] = defaultdict(list)
        self._entry: str | None = None
        self._compiled = False
        self.warnings: list[str] = []

    # -- construction ------------------------------------------------------

    def add_node(self, node: Node) -> Graph:
        if node.name in self._nodes:
            raise GraphValidationError(f"duplicate node name: {node.name!r}")
        self._nodes[node.name] = node
        self._compiled = False
        return self

    def add_edge(self, source: str, target: str, when: Condition | None = None) -> Graph:
        self._edges.append(Edge(source=source, target=target, when=when))
        self._compiled = False
        return self

    def set_entry(self, name: str) -> Graph:
        self._entry = name
        self._compiled = False
        return self

    # -- validation & compile ---------------------------------------------

    def validate(self) -> list[str]:
        """Raise on hard errors; return a list of soft warnings."""
        if self._entry is None:
            raise GraphValidationError("no entry node set")
        if self._entry not in self._nodes:
            raise GraphValidationError(f"entry node {self._entry!r} is not registered")

        for edge in self._edges:
            if edge.source not in self._nodes:
                raise GraphValidationError(
                    f"edge source {edge.source!r} is not a registered node"
                )
            if edge.target != END and edge.target not in self._nodes:
                raise GraphValidationError(
                    f"edge target {edge.target!r} is not a registered node"
                )

        warnings: list[str] = []
        reachable = self._reachable_from_entry()
        for name in self._nodes:
            if name not in reachable:
                warnings.append(
                    f"node {name!r} is unreachable via static edges "
                    "(only reachable via dynamic Command.goto, if at all)"
                )
        return warnings

    def compile(self) -> Graph:
        self.warnings = self.validate()
        self._edges_from = defaultdict(list)
        for edge in self._edges:
            self._edges_from[edge.source].append(edge)
        self._compiled = True
        return self

    def _reachable_from_entry(self) -> set[str]:
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in self._edges:
            if edge.target != END:
                adj[edge.source].append(edge.target)
        seen: set[str] = set()
        queue: deque[str] = deque([self._entry] if self._entry else [])
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            queue.extend(adj.get(cur, []))
        return seen

    # -- execution ---------------------------------------------------------

    async def run(
        self, state: State, *, max_steps: int = 100, hooks: Hooks | None = None
    ) -> State:
        if not self._compiled:
            self.compile()

        current: str | None = self._entry
        steps = 0
        while current is not None and current != END:
            if steps >= max_steps:
                raise GraphExecutionError(
                    f"max_steps ({max_steps}) exceeded in graph {self.name!r}; "
                    "possible unbounded loop"
                )
            steps += 1
            node = self._nodes[current]
            before = state.snapshot_scratch()
            if hooks:
                await safe_fire(hooks.on_node_start, current, state)
            t0 = time.perf_counter()

            try:
                cmd = await node.run(state)
            except Exception as exc:  # noqa: BLE001 - recorded then re-raised
                dur = (time.perf_counter() - t0) * 1000
                state.trace.append(
                    StepTrace(
                        node=current,
                        scratch_before=before,
                        duration_ms=dur,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                if hooks:
                    await safe_fire(hooks.on_node_error, current, state, exc)
                raise GraphExecutionError(f"node {current!r} failed: {exc}") from exc

            dur = (time.perf_counter() - t0) * 1000
            if cmd is not None and cmd.update:
                state.merge(cmd.update)

            nxt = self._resolve_next(current, cmd, state)
            step = StepTrace(
                node=current,
                scratch_before=before,
                duration_ms=dur,
                goto=cmd.goto if cmd else None,
                next=nxt,
            )
            state.trace.append(step)
            if hooks:
                await safe_fire(hooks.on_node_end, current, state, step)
            current = nxt

        return state

    def _resolve_next(self, current: str, cmd: Command | None, state: State) -> str:
        if cmd is not None and cmd.goto is not None:
            return cmd.goto
        for edge in self._edges_from.get(current, []):
            if edge.matches(state):
                return edge.target
        return END
