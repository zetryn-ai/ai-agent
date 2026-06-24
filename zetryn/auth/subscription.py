"""Subscription auth seam.

Gates access to the Zetryn agent + hosted models. The deal: using public providers
(Groq/Gemini/...) with your own key is unmetered by Zetryn; but using the agent at all
requires a valid Zetryn subscription (Free tier minimum). Plans (Free/Basic/Pro/Max)
carry per-model rate limits (TPM/RPM/RPD), enforced server-side for Zetryn models.

This module is a SEAM: ``LocalSubscriptionAuth`` validates locally (stub) so the
architecture is ready. Real enforcement is server-side at the Lema/Zetryn platform;
a ``RemoteSubscriptionAuth`` (HTTP to the platform) replaces the stub later without
touching callers. ``License`` adds lightweight cached validation (not per-run).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Model tiers (analogous to Opus/Sonnet/Haiku).
MODEL_TIERS = ("easfus", "medifus", "hardes")


@dataclass
class RateLimit:
    """Per-model limits. None means unlimited. Real numbers come from the platform."""

    tpm: int | None = None  # tokens per minute
    rpm: int | None = None  # requests per minute
    rpd: int | None = None  # requests per day


# Plan presets. NUMBERS ARE PLACEHOLDERS — the platform is the source of truth.
PLAN_PRESETS: dict[str, dict] = {
    "free": {
        "models": ["easfus"],
        "limits": {"easfus": RateLimit(tpm=10_000, rpm=10, rpd=200)},
    },
    "basic": {
        "models": ["easfus", "medifus"],
        "limits": {
            "easfus": RateLimit(tpm=50_000, rpm=30, rpd=2_000),
            "medifus": RateLimit(tpm=30_000, rpm=20, rpd=1_000),
        },
    },
    "pro": {
        "models": ["easfus", "medifus", "hardes"],
        "limits": {
            "easfus": RateLimit(tpm=200_000, rpm=100, rpd=20_000),
            "medifus": RateLimit(tpm=150_000, rpm=60, rpd=10_000),
            "hardes": RateLimit(tpm=80_000, rpm=30, rpd=3_000),
        },
    },
    "max": {
        "models": ["easfus", "medifus", "hardes"],
        "limits": {m: RateLimit() for m in MODEL_TIERS},  # unlimited
    },
}


@dataclass
class Entitlement:
    """Result of verifying a subscription key."""

    valid: bool
    tier: str | None = None  # plan: free | basic | pro | max
    models: list[str] = field(default_factory=list)  # allowed Zetryn model tiers
    limits: dict[str, RateLimit] = field(default_factory=dict)  # per-model limits
    reason: str | None = None


@runtime_checkable
class SubscriptionAuth(Protocol):
    """Verifies a subscription key and returns what it entitles."""

    async def verify(self, key: str | None) -> Entitlement: ...


class LocalSubscriptionAuth:
    """Stub validator for development.

    Accepts any non-empty key and grants a plan's entitlements from ``PLAN_PRESETS``.
    Replace with ``RemoteSubscriptionAuth`` (calls the platform) for production.
    """

    def __init__(
        self,
        *,
        plan: str = "max",
        models: tuple[str, ...] | None = None,
    ) -> None:
        self._plan = plan
        preset = PLAN_PRESETS.get(plan, {})
        self._models = (
            list(models) if models is not None else preset.get("models", list(MODEL_TIERS))
        )
        self._limits = preset.get("limits", {})

    async def verify(self, key: str | None) -> Entitlement:
        if not key:
            return Entitlement(valid=False, reason="no subscription key provided")
        # TODO(platform): POST https://api.zetryn.com/v1/auth/verify and use the
        # real plan + models + limits from the response.
        return Entitlement(
            valid=True,
            tier=self._plan,
            models=self._models,
            limits={m: self._limits.get(m, RateLimit()) for m in self._models},
        )


class License:
    """Lightweight, cached license validation — NOT per-run.

    Validates once, caches for ``ttl_s``, and tolerates transient auth-server
    failures for ``grace_s`` (keeps the last good entitlement). This is what makes
    the agent gate cheap: we only check the license is valid, never meter BYO-provider
    usage (Zetryn-model usage is metered server-side).
    """

    def __init__(
        self,
        key: str | None,
        *,
        auth: SubscriptionAuth | None = None,
        ttl_s: float = 3600.0,
        grace_s: float = 86_400.0,
    ) -> None:
        self._key = key
        self._auth = auth or LocalSubscriptionAuth()
        self._ttl_s = ttl_s
        self._grace_s = grace_s
        self._cached: Entitlement | None = None
        self._checked_at: float = 0.0

    async def entitlement(self) -> Entitlement:
        now = time.monotonic()
        if self._cached is not None and (now - self._checked_at) < self._ttl_s:
            return self._cached
        try:
            ent = await self._auth.verify(self._key)
            self._cached = ent
            self._checked_at = now
            return ent
        except Exception as exc:  # noqa: BLE001 - network blip → grace period
            if self._cached is not None and (now - self._checked_at) < self._grace_s:
                return self._cached
            return Entitlement(valid=False, reason=f"auth unavailable: {exc}")

    async def assert_active(self) -> Entitlement:
        ent = await self.entitlement()
        if not ent.valid:
            raise PermissionError(f"Zetryn subscription required: {ent.reason}")
        return ent
