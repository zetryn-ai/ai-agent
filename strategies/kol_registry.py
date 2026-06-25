"""Typed lookup of KOL profiles from a `KnowledgePack`.

The bot ships a `kol_whitelist.json` inside its pack. The framework reads
it and exposes per-wallet `KOLProfile` lookups + the global thresholds
the user authored at the top of the file.

Boundary: the framework never computes hit-rate or scores wallets — the
bot computes those offline (from on-chain history, Cielo, GMGN, etc.)
and ships the result as JSON.
"""

from __future__ import annotations

from typing import Any

from trading.schemas import KOLProfile
from zetryn.knowledge import KnowledgePack


class KOLRegistry:
    """Read-only view of a pack's KOL whitelist."""

    _TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}

    def __init__(
        self,
        wallets: dict[str, KOLProfile],
        *,
        min_tier: str = "C",
        min_hit_rate: float = 0.0,
    ) -> None:
        self._wallets = dict(wallets)
        self._min_tier = min_tier
        self._min_hit_rate = min_hit_rate

    # -- construction ------------------------------------------------------

    @classmethod
    def from_pack(
        cls, pack: KnowledgePack, *, namespace: str = "kol_whitelist"
    ) -> KOLRegistry:
        """Build a registry from `pack.data/<namespace>.json`.

        Expected JSON shape:
            {
              "wallets": { "<address>": { ...KOLProfile fields... } },
              "min_tier_to_copy": "A",
              "min_hit_rate": 0.40
            }

        Returns an empty registry (with permissive defaults) if the pack
        does not contain the namespace — callers can then short-circuit
        cleanly with action="skip" rather than crash.
        """
        raw = pack.lookup(namespace)
        if not isinstance(raw, dict):
            return cls({})

        wallets_raw = raw.get("wallets") or {}
        wallets: dict[str, KOLProfile] = {}
        for address, profile_data in wallets_raw.items():
            if not isinstance(profile_data, dict):
                continue
            wallets[address] = KOLProfile.model_validate(profile_data)

        return cls(
            wallets,
            min_tier=str(raw.get("min_tier_to_copy", "C")),
            min_hit_rate=float(raw.get("min_hit_rate", 0.0)),
        )

    # -- queries -----------------------------------------------------------

    def get(self, wallet: str) -> KOLProfile | None:
        return self._wallets.get(wallet)

    def is_known(self, wallet: str) -> bool:
        return wallet in self._wallets

    def passes_global_floor(self, profile: KOLProfile) -> bool:
        """True if this profile clears the pack-wide minimum thresholds."""
        if profile.hit_rate < self._min_hit_rate:
            return False
        my_tier = self._TIER_ORDER.get(profile.tier, 99)
        floor = self._TIER_ORDER.get(self._min_tier, 99)
        return my_tier <= floor

    @property
    def min_tier(self) -> str:
        return self._min_tier

    @property
    def min_hit_rate(self) -> float:
        return self._min_hit_rate

    def as_dict(self) -> dict[str, Any]:
        """Debug helper — dump everything as plain dicts."""
        return {
            "min_tier": self._min_tier,
            "min_hit_rate": self._min_hit_rate,
            "wallets": {addr: p.model_dump() for addr, p in self._wallets.items()},
        }

    # -- dunders -----------------------------------------------------------

    def __len__(self) -> int:
        return len(self._wallets)

    def __bool__(self) -> bool:
        return bool(self._wallets)

    def __contains__(self, wallet: str) -> bool:
        return wallet in self._wallets
