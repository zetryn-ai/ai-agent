"""A generic decision log built on a MemoryStore.

Stores one record per run (plain dicts, so core stays domain-agnostic — the trading
layer passes ``decision.model_dump()``). The bot later attaches the realized outcome
via ``record_outcome``, which makes evaluation and backtesting possible.
"""

from __future__ import annotations

from typing import Any

from .store import MemoryStore

_NS = "decisions"


class DecisionLog:
    def __init__(self, store: MemoryStore, *, namespace: str = _NS) -> None:
        self._store = store
        self._ns = namespace

    async def log(self, run_id: str, record: dict[str, Any]) -> None:
        await self._store.put(self._ns, run_id, {"run_id": run_id, "outcome": None, **record})

    async def record_outcome(self, run_id: str, outcome: dict[str, Any]) -> None:
        entry = await self._store.get(self._ns, run_id)
        if entry is None:
            entry = {"run_id": run_id}
        entry["outcome"] = outcome
        await self._store.put(self._ns, run_id, entry)

    async def all(self) -> list[dict]:
        return await self._store.query(self._ns)

    async def stats(self) -> dict[str, Any]:
        """Aggregate counts by action and PnL stats from recorded outcomes."""
        records = await self.all()
        by_action: dict[str, int] = {}
        wins = trades = 0
        total_pnl = 0.0
        for r in records:
            action = r.get("action", "unknown")
            by_action[action] = by_action.get(action, 0) + 1
            outcome = r.get("outcome")
            if outcome and "pnl" in outcome:
                trades += 1
                total_pnl += outcome["pnl"]
                if outcome["pnl"] > 0:
                    wins += 1
        return {
            "total": len(records),
            "by_action": by_action,
            "trades_with_outcome": trades,
            "win_rate": round(wins / trades, 4) if trades else None,
            "total_pnl": round(total_pnl, 4),
        }
