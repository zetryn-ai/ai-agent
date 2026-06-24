"""A generic blacklist built on a MemoryStore.

Keys (token mints, dev wallets, anything) flagged with a reason and optional TTL.
Checking a blacklist before expensive work (LLM calls, deep analysis) is a cheap win.
"""

from __future__ import annotations

from .store import MemoryStore

_NS = "blacklist"


class Blacklist:
    def __init__(self, store: MemoryStore, *, namespace: str = _NS) -> None:
        self._store = store
        self._ns = namespace

    async def add(self, key: str, reason: str = "", *, ttl: float | None = None) -> None:
        await self._store.put(self._ns, key, {"key": key, "reason": reason}, ttl=ttl)

    async def is_blacklisted(self, key: str) -> bool:
        return (await self._store.get(self._ns, key)) is not None

    async def reason(self, key: str) -> str | None:
        entry = await self._store.get(self._ns, key)
        return entry.get("reason") if entry else None

    async def remove(self, key: str) -> None:
        await self._store.delete(self._ns, key)

    async def all(self) -> list[dict]:
        return await self._store.query(self._ns)
