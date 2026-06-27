"""Typed lookup of SmartWalletProfiles from a `KnowledgePack`.

The bot ships a `smart_wallet_whitelist.json` inside its pack. The
framework reads it and exposes per-wallet `SmartWalletProfile` lookups
plus the global thresholds the user authored at the top of the file.

Boundary: the framework never computes hit-rate or scores wallets — the
bot computes those offline (from on-chain history, Cielo, GMGN, etc.)
and ships the result as JSON.
"""

from __future__ import annotations

from typing import Any

from trading.schemas import SmartWalletProfile
from zetryn.knowledge import KnowledgePack


class SmartWalletRegistry:
    """Read-only view of a pack's smart wallet whitelist."""

    _TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}

    def __init__(
        self,
        wallets: dict[str, SmartWalletProfile],
        *,
        min_tier: str = "C",
        min_hit_rate: float = 0.0,
    ) -> None:
        self._wallets = dict(wallets)
        self._min_tier = min_tier
        self._min_hit_rate = min_hit_rate

    # -- construction -------------------------------------------------------

    @classmethod
    def from_pack(
        cls, pack: KnowledgePack, *, namespace: str = "smart_wallet_whitelist"
    ) -> SmartWalletRegistry:
        """Build a registry from `pack.data/<namespace>.json`.

        Expected JSON shape:
            {
              "wallets": { "<address>": { ...SmartWalletProfile fields... } },
              "min_tier_to_use": "B",
              "min_hit_rate": 0.35
            }

        Returns an empty registry (permissive defaults) if the pack does
        not contain the namespace — nodes short-circuit cleanly.
        """
        raw = pack.lookup(namespace)
        if not isinstance(raw, dict):
            return cls({})

        wallets_raw = raw.get("wallets") or {}
        wallets: dict[str, SmartWalletProfile] = {}
        for address, profile_data in wallets_raw.items():
            if not isinstance(profile_data, dict):
                continue
            wallets[address] = SmartWalletProfile.model_validate(profile_data)

        return cls(
            wallets,
            min_tier=str(raw.get("min_tier_to_use", "C")),
            min_hit_rate=float(raw.get("min_hit_rate", 0.0)),
        )

    # -- queries -----------------------------------------------------------

    def get(self, wallet: str) -> SmartWalletProfile | None:
        return self._wallets.get(wallet)

    def is_known(self, wallet: str) -> bool:
        return wallet in self._wallets

    def passes_global_floor(self, profile: SmartWalletProfile) -> bool:
        """True if profile clears the pack-wide minimum thresholds."""
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
