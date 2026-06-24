"""Persistent memory: a small key-value interface with pluggable backends.

The framework defines the interface; backends are swappable via config. Default
backends ship here (in-memory, JSON file); Redis/SQLite/vector come later.

Values are namespaced (``ns``) so different concerns (blacklist, decisions, ...)
don't collide. TTL is optional; expired entries are treated as absent.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryStore(Protocol):
    """Namespaced key-value store."""

    async def get(self, ns: str, key: str) -> Any | None: ...
    async def put(self, ns: str, key: str, value: Any, *, ttl: float | None = None) -> None: ...
    async def delete(self, ns: str, key: str) -> None: ...
    async def query(self, ns: str) -> list[Any]: ...


def _expired(entry: dict) -> bool:
    exp = entry.get("exp")
    return exp is not None and exp <= time.time()


class InMemoryStore:
    """Zero-setup dict-backed store. Default for tests and ephemeral runs."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict]] = {}

    async def get(self, ns: str, key: str) -> Any | None:
        entry = self._data.get(ns, {}).get(key)
        if entry is None or _expired(entry):
            return None
        return entry["value"]

    async def put(self, ns: str, key: str, value: Any, *, ttl: float | None = None) -> None:
        exp = time.time() + ttl if ttl is not None else None
        self._data.setdefault(ns, {})[key] = {"value": value, "exp": exp}

    async def delete(self, ns: str, key: str) -> None:
        self._data.get(ns, {}).pop(key, None)

    async def query(self, ns: str) -> list[Any]:
        bucket = self._data.get(ns, {})
        return [e["value"] for e in bucket.values() if not _expired(e)]


class JSONFileStore:
    """Simple cross-run persistence to a single JSON file.

    Loads on init, writes on every mutation. Fine for modest data; swap for Redis
    when throughput matters.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: dict[str, dict[str, dict]] = {}
        if self._path.exists():
            self._data = json.loads(self._path.read_text() or "{}")

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data))

    async def get(self, ns: str, key: str) -> Any | None:
        entry = self._data.get(ns, {}).get(key)
        if entry is None or _expired(entry):
            return None
        return entry["value"]

    async def put(self, ns: str, key: str, value: Any, *, ttl: float | None = None) -> None:
        exp = time.time() + ttl if ttl is not None else None
        self._data.setdefault(ns, {})[key] = {"value": value, "exp": exp}
        self._flush()

    async def delete(self, ns: str, key: str) -> None:
        self._data.get(ns, {}).pop(key, None)
        self._flush()

    async def query(self, ns: str) -> list[Any]:
        bucket = self._data.get(ns, {})
        return [e["value"] for e in bucket.values() if not _expired(e)]
