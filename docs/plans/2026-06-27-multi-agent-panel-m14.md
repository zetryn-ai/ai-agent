# M14 — Multi-Agent Panel (rule-based orchestrator)

**Date:** 2026-06-27
**Status:** Shipped (v0.18.0, branch `feat/dev/multi-agent-panel`)
**Release target:** tentative v1.1.0 — final placement TBD; may slip out of
v1.0.0 since v1.0.0 is ~90% ready and remaining work is real-source testing.

Rule-based panel that runs multiple specialist sub-graphs and merges their
verdicts. Two node types (`PanelNode`, `PanelDecisionNode`) mirror the
existing `LLMNode` / `LLMDecisionNode` pair.

LLM-orchestrator variant (Anthropic-style adaptive dispatch) is **explicitly
out of scope** here — deferred to v3.0.0 to preserve the "framework decides,
bot executes" narrative. The framework stays a transparent computation
engine; orchestration logic lives in user-supplied Python.

## 1. Tujuan

1. Strategi bisa mengonsultasikan N specialist sub-graph yang ahli di domain
   berbeda (safety, market, social, risk, …) dalam **satu langkah graph**,
   tanpa user perlu wire edges + scratch propagation sendiri.
2. Orchestration tetap **deterministik dan auditable** — siapa specialist
   yang dipanggil, dengan input apa, di urutan apa, ditentukan user di
   kode Python, bukan oleh LLM.
3. Boundary "framework decides, bot executes" tetap **literal dan spirit**
   utuh: framework tidak gain agency baru, cuma menambah primitif
   coordination yang sudah eksplisit.

## 2. Keputusan desain (final)

Enam keputusan kunci dikunci lewat brainstorming:

| # | Topik | Pilihan | Alasan singkat |
|---|---|---|---|
| 1 | Orchestrator | **Rule-based Python** (no LLM-as-orchestrator) | Konsisten dengan "advisor inside guardrails" filosofi; predictable, auditable, hemat token. LLM-orchestrator → v3.0.0 |
| 2 | Execution mode | **Configurable** `parallel` (default) atau `sequential` | Scanner-style butuh paralel (latency), KOL-style butuh sequential (safety-gate-first). DAG mode → defer |
| 3 | Specialist shape | **Sub-graph (`Graph`) saja** | Reusable standalone, audit clean, konsisten dengan `AgentNode`. Helper `single_llm_specialist` untuk simple case |
| 4 | State scoping | **Isolasi + `scratch["_panel"]` channel** | Specialist fresh state with parent context; sequential mode auto-injects prior results via reserved scratch key |
| 5 | Node shape | **Dua kelas**: `PanelNode` + `PanelDecisionNode` | Mirror persis `LLMNode` / `LLMDecisionNode`. Type-readable di builder |
| 6 | Failure + short-circuit | **Graceful default + escape hatch** (`required=`, `short_circuit_on=`) | Konsisten dengan graceful-degradation Zetryn; opt-in granularity |

## 3. Public API

### `PanelNode` — intermediate panel

```python
from zetryn.panel import PanelNode

PanelNode(
    name: str,                                  # node name, scratch output_key default
    specialists: dict[str, Graph],              # name → sub-graph (insertion order matters
                                                #   for `sequential` mode)
    aggregator: Aggregator,                     # (results, state) -> Any → scratch[output_key]
    *,
    mode: Literal["parallel", "sequential"] = "parallel",
    output_key: str | None = None,              # default = name
    required: Sequence[str] = (),               # specialists whose failure raises
    short_circuit_on: ShortCircuitFn | None = None,  # sequential only
)
```

### `PanelDecisionNode` — terminal panel

```python
from zetryn.panel import PanelDecisionNode

PanelDecisionNode(
    name: str,
    specialists: dict[str, Graph],
    aggregator: Aggregator,                     # (results, state) -> Any → state.output
    *,
    mode: Literal["parallel", "sequential"] = "parallel",
    goto: str = END,                            # next target after panel decision
    required: Sequence[str] = (),
    short_circuit_on: ShortCircuitFn | None = None,
)
```

### Type aliases

```python
Aggregator = Callable[[dict[str, Any], State], Any]
# Args:
#   results: {specialist_name: specialist.state.output} — None entries for failed optionals
#   state:   parent State (read-only conceptually; read context, scratch beyond _panel,
#                          knowledge pack lookups, etc.)
# Returns:
#   PanelNode → written to state.scratch[output_key]
#   PanelDecisionNode → written to state.output

ShortCircuitFn = Callable[[dict[str, Any], State], Any | None]
# Args:
#   results: {specialist_name: output} — only specialists that have run so far
#   state:   parent State
# Returns:
#   None → continue to next specialist
#   non-None → abort panel; this value becomes the panel output
#     (aggregator NOT called)
```

### Errors

```python
class PanelExecutionError(Exception):
    """Raised when a required specialist fails."""
```

`PanelExecutionError` re-raised through `Graph.run` as
`GraphExecutionError(f"node {panel_name!r} failed: ...")` — matches existing
node-failure semantics.

## 4. Execution semantik

### Parallel mode
1. Validate at construction: `short_circuit_on` MUST be `None` (would be
   silently ignored otherwise). ValueError at build time.
2. For each specialist, build `sub_state = State(context=parent.context,
   scratch={"_panel": {}})`. Empty `_panel` because no prior results in
   parallel.
3. `await asyncio.gather(*(g.run(s) for s, g in ...))` — true parallel.
4. For each outcome:
   - Success → `results[name] = final_state.output`
   - Failure & name in `required` → raise `PanelExecutionError`
   - Failure & name NOT in required → `results[name] = None`,
     `failures[name] = "<ExcType>: <msg>"`
5. After all specialists done: optionally write
   `state.scratch["_panel_failures"][panel_name] = failures` (only if
   non-empty).
6. Call `aggregator(results, state)`. Write result to scratch (PanelNode)
   or state.output (PanelDecisionNode).

### Sequential mode
1. Iterate `specialists.items()` in insertion order.
2. For each specialist:
   - `sub_state = State(context=parent.context, scratch={"_panel":
     dict(results)})` — snapshot of accumulated results.
   - Run. On success → `results[name] = final_state.output`. On failure →
     same `required` semantic as parallel.
   - If `short_circuit_on` is set: call it with `(results, state)`. If it
     returns non-None, set `sc_value = return`, break loop.
3. After loop:
   - If `sc_value is not None`: write `sc_value` as panel output (skip
     aggregator).
   - Else: call `aggregator(results, state)` and write result.
4. `_panel_failures` flag set same as parallel.

### Order guarantees
- `specialists: dict[str, Graph]` relies on Python 3.7+ dict insertion
  order (already required by `requires-python = ">=3.11"`).
- Specialist execution order in sequential mode = dict insertion order.
- In parallel mode, order is undefined (asyncio.gather), but `results`
  dict is rebuilt in specialists' insertion order before passing to
  aggregator (for stable downstream comparison).

## 5. State conventions

Two reserved scratch keys introduced by panel:

| Key | Owner | Lifetime | Format |
|---|---|---|---|
| `scratch["_panel"]` | Specialist sub-state | per specialist run | `{prior_specialist_name: prior_output}` |
| `scratch["_panel_failures"]` | Parent state | persists | `{panel_name: {failed_specialist_name: error_str}}` |

User code MUST NOT write to these keys directly. Reading is fine and
expected (specialists reading `_panel`; aggregator reading
`_panel_failures` to weight confidence).

## 6. Helper for simple specialists

To address the "specialist with 1 LLM is annoying boilerplate" concern,
ship a single helper:

```python
from zetryn.panel import single_llm_specialist

safety_spec = single_llm_specialist(
    name="safety_specialist",
    client=llm,
    schema=SafetyVerdict,
    prompt_fn=safety_prompt,
    # optional: output_key, fallback_fn, model, max_attempts
)
# Returns a Graph with a single LLMNode and entry set; output = LLMNode result
```

Internally builds a 1-node Graph that wraps `LLMNode` and writes its result
to `state.output` via a trailing RuleNode. This is just sugar — user can
always build their own multi-node Graph for richer specialists.

## 7. Validation pada konstruksi

Both Panel*Node constructors validate at `__init__`:

- `specialists` non-empty dict (raise ValueError)
- Every value in specialists is a `Graph` (raise TypeError)
- `aggregator` is callable (raise TypeError)
- `mode` ∈ {`"parallel"`, `"sequential"`} (raise ValueError)
- If `mode == "parallel"` and `short_circuit_on is not None` → ValueError
  ("short_circuit_on is only meaningful in sequential mode")
- Every name in `required` exists in `specialists` (raise ValueError)
- `short_circuit_on` if set must be callable (raise TypeError)

## 8. Out of scope (defer)

- **LLM orchestrator** — Anthropic-style adaptive dispatch. → v3.0.0.
- **DAG mode** with per-specialist `depends_on`. → M14.1 if real use case
  appears.
- **YAML loader support** (`type: panel`). → M14.1 after panel API stable
  and at least one strategy uses it in production.
- **Per-specialist timeout**. → Add `timeouts: dict[str, float]` parameter
  as additive option when needed.
- **Built-in aggregator library** (weighted_average, majority_vote, …) →
  Ship one example aggregator inside the example file for now; library
  emerges from usage patterns.

## 9. Rencana test

- `test_panel_parallel.py` — happy path parallel, scratch isolation
  (specialist tidak lihat siblings via _panel di parallel), failure
  optional, failure required → PanelExecutionError, aggregator dipanggil
  dengan results+state.
- `test_panel_sequential.py` — happy path sequential, `_panel` propagation
  (specialist N+1 lihat hasil N), short-circuit (predicate returns value
  → abort + skip remaining + aggregator NOT called), required failure
  raises.
- `test_panel_decision.py` — `PanelDecisionNode` terminates dengan
  `Command(goto=END)`, custom `goto` supported, state.output ditulis,
  short-circuit value sampai ke state.output.
- `test_panel_validation.py` — construction-time guards (empty
  specialists, non-callable aggregator, parallel + short_circuit_on, etc).
- `test_panel_helper.py` — `single_llm_specialist` builds valid 1-node
  Graph yang runnable.

## 10. Dependensi

Tidak ada dependensi baru. Stdlib `asyncio` cukup. Reuse existing core
primitives.

## 11. Release

- Versi bump: 0.17.0 → **0.18.0**
- CHANGELOG entry.
- Update `docs/plans/README.md` row → Shipped (v0.18.0) once merged.
- Update `docs/CAPABILITIES.md` M14 row status.
- Branch: `feat/dev/multi-agent-panel` — merge tactic TBD by user
  (squash/rebase decided at PR time).
