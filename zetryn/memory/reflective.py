"""Reflective node: read past decisions, extract loss patterns, inject lessons.

`ReflectiveNode` runs before the narrative LLM call. It scans the last N
decisions in a `DecisionLog`, groups losers by feature buckets, and writes a
compact "lessons" summary back into `state.scratch`. The downstream prompt
builder can then prepend that summary to its system message.

This is a deterministic, rule-based extractor — no LLM call here. It is meant
to be cheap and predictable, suitable for live trading loops. A heavier
LLM-based reflector can be layered later as an `AgentNode`.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from zetryn.core.state import Command, State

from .decision_log import DecisionLog


@dataclass
class Pattern:
    """One observed loss pattern: a (feature, bucket) pair with stats."""

    feature: str
    bucket: str
    loss_count: int
    total_count: int
    avg_pnl: float
    losses_pnl: list[float] = field(default_factory=list)

    @property
    def loss_rate(self) -> float:
        return self.loss_count / self.total_count if self.total_count else 0.0

    def describe(self) -> str:
        return (
            f"{self.feature} = {self.bucket}: "
            f"{self.loss_count}/{self.total_count} losses "
            f"(rate {self.loss_rate:.0%}, avg pnl {self.avg_pnl:+.1%})"
        )


@dataclass
class ReflectionResult:
    """Output of a single reflection pass — what gets written to scratch."""

    window: int
    total_decisions: int
    total_losses: int
    avg_loss_pnl: float | None
    patterns: list[Pattern]
    losing_ids: list[str]

    def to_text(self, *, max_lines: int = 5) -> str:
        if self.total_decisions == 0:
            return "No prior decisions on record."
        if self.total_losses == 0:
            return (
                f"Reviewed last {self.total_decisions} decisions — no losses recorded."
            )
        head = (
            f"Reviewed last {self.total_decisions} decisions: "
            f"{self.total_losses} losers"
        )
        if self.avg_loss_pnl is not None:
            head += f" (avg pnl {self.avg_loss_pnl:+.1%})"
        head += "."
        if self.losing_ids:
            head += (
                " Recent losers: "
                + ", ".join(self.losing_ids[:5])
                + ("..." if len(self.losing_ids) > 5 else "")
            )

        lines = [head]
        if self.patterns:
            lines.append("Loss patterns to avoid:")
            for p in self.patterns[:max_lines]:
                lines.append(f"  - {p.describe()}")
        return "\n".join(lines)


def _is_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _quartile_label(values: list[float], v: float) -> str:
    """Return a coarse bucket label for `v` based on the population `values`."""
    if not values:
        return f"~{v:.3g}"
    s = sorted(values)
    n = len(s)
    q1 = s[n // 4]
    q2 = s[n // 2]
    q3 = s[(3 * n) // 4]
    if v <= q1:
        return f"<= {q1:.3g}"
    if v <= q2:
        return f"{q1:.3g}..{q2:.3g}"
    if v <= q3:
        return f"{q2:.3g}..{q3:.3g}"
    return f"> {q3:.3g}"


def reflect(
    records: list[dict[str, Any]],
    *,
    feature_keys: list[str] | None = None,
    loss_threshold: float = 0.0,
    top_k: int = 5,
) -> ReflectionResult:
    """Pure function: derive loss patterns from a list of decision records."""
    # Only consider records with a realised outcome.
    with_outcome = [
        r for r in records if isinstance(r.get("outcome"), dict) and "pnl" in r["outcome"]
    ]
    losses = [r for r in with_outcome if r["outcome"]["pnl"] < loss_threshold]

    avg_loss = (
        statistics.mean(r["outcome"]["pnl"] for r in losses) if losses else None
    )

    keys = feature_keys or _infer_feature_keys(with_outcome)
    patterns: list[Pattern] = []
    for key in keys:
        values_all = [r.get(key) for r in with_outcome if r.get(key) is not None]
        if not values_all:
            continue
        numeric = all(_is_numeric(v) for v in values_all)
        # Bucket every record (numeric → quartile, else value-as-string).
        if numeric:
            pop = [float(v) for v in values_all]

            def bucket_of(r: dict[str, Any], _k: str = key, _pop: list[float] = pop) -> str | None:
                v = r.get(_k)
                if v is None:
                    return None
                return _quartile_label(_pop, float(v))
        else:
            def bucket_of(r: dict[str, Any], _k: str = key) -> str | None:
                v = r.get(_k)
                return None if v is None else str(v)

        per_bucket: dict[str, list[dict[str, Any]]] = {}
        for r in with_outcome:
            b = bucket_of(r)
            if b is not None:
                per_bucket.setdefault(b, []).append(r)

        for bucket, rs in per_bucket.items():
            bucket_losses = [r for r in rs if r["outcome"]["pnl"] < loss_threshold]
            if not bucket_losses:
                continue
            patterns.append(
                Pattern(
                    feature=key,
                    bucket=bucket,
                    loss_count=len(bucket_losses),
                    total_count=len(rs),
                    avg_pnl=statistics.mean(r["outcome"]["pnl"] for r in rs),
                    losses_pnl=[r["outcome"]["pnl"] for r in bucket_losses],
                )
            )

    patterns.sort(key=lambda p: (-p.loss_count, p.avg_pnl))
    losing_ids = [r.get("run_id") or r.get("id") or "?" for r in losses]

    return ReflectionResult(
        window=len(records),
        total_decisions=len(with_outcome),
        total_losses=len(losses),
        avg_loss_pnl=avg_loss,
        patterns=patterns[:top_k],
        losing_ids=losing_ids,
    )


def _infer_feature_keys(records: list[dict[str, Any]]) -> list[str]:
    """Pick top-level keys that look like features (not run_id / action / outcome)."""
    skip = {"run_id", "id", "outcome", "action", "timestamp"}
    seen: dict[str, int] = {}
    for r in records:
        for k in r.keys():
            if k in skip:
                continue
            seen[k] = seen.get(k, 0) + 1
    return [k for k, _ in sorted(seen.items(), key=lambda kv: -kv[1])]


class ReflectiveNode:
    """Graph node: load recent decisions and write a lessons block to scratch.

    Writes two scratch keys derived from `output_key` (default `"lessons"`):
      - `lessons`  → `ReflectionResult` dataclass (structured)
      - `lessons_text` → human-readable summary string, ready for prompts
    """

    def __init__(
        self,
        name: str,
        decision_log: DecisionLog,
        *,
        window: int = 20,
        output_key: str = "lessons",
        feature_keys: list[str] | None = None,
        loss_threshold: float = 0.0,
        top_k: int = 5,
    ) -> None:
        if window <= 0:
            raise ValueError("window must be > 0")
        self.name = name
        self._log = decision_log
        self._window = window
        self._output_key = output_key
        self._feature_keys = feature_keys
        self._loss_threshold = loss_threshold
        self._top_k = top_k

    async def run(self, state: State) -> Command | None:
        all_records = await self._log.all()
        recent = all_records[-self._window :] if all_records else []
        result = reflect(
            recent,
            feature_keys=self._feature_keys,
            loss_threshold=self._loss_threshold,
            top_k=self._top_k,
        )
        state.scratch[self._output_key] = result
        state.scratch[f"{self._output_key}_text"] = result.to_text()
        return None
