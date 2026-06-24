"""Mandatory API-key pool with rotation.

Free-tier providers rate-limit aggressively. The pool holds multiple keys and
rotates round-robin, taking a key out of circulation for a cooldown window when it
returns 429. This multiplies free-tier quota legally.
"""

from __future__ import annotations

import time

from .types import NoKeysAvailableError


class KeyPool:
    """Round-robin pool of API keys with per-key cooldown on rate limit."""

    def __init__(self, keys: list[str], *, cooldown_s: float = 60.0) -> None:
        if not keys:
            raise ValueError("KeyPool requires at least one key")
        self._keys = list(keys)
        self._cooldown_s = cooldown_s
        self._idx = 0
        self._cooling: dict[str, float] = {}  # key -> monotonic time when usable again

    def __len__(self) -> int:
        return len(self._keys)

    def _now(self) -> float:
        return time.monotonic()

    def acquire(self) -> str:
        """Return the next available key, skipping those still cooling down."""
        now = self._now()
        n = len(self._keys)
        for _ in range(n):
            key = self._keys[self._idx]
            self._idx = (self._idx + 1) % n
            if self._cooling.get(key, 0.0) <= now:
                return key
        # All keys are cooling — surface the soonest availability.
        soonest = min(self._cooling.values()) - now
        raise NoKeysAvailableError(
            f"all {n} keys are rate-limited; next available in {soonest:.1f}s"
        )

    def penalize(self, key: str, *, cooldown_s: float | None = None) -> None:
        """Put a key on cooldown after a rate-limit response."""
        self._cooling[key] = self._now() + (cooldown_s or self._cooldown_s)

    def available(self) -> int:
        now = self._now()
        return sum(1 for k in self._keys if self._cooling.get(k, 0.0) <= now)
