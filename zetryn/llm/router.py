"""Multi-provider LLM router with per-model throttle enforcement.

`LLMRouter` wraps several `LLMClient` instances (e.g. Groq, OpenRouter, Gemini)
and implements the same `LLMClient` protocol, so any `LLMNode` can use it
unchanged. On rate-limit, quota exhaustion, or transient provider failure, the
router fails over to the next entry in declaration order.

Throttle enforcement is local and best-effort: each entry may declare a
`RateLimit(tpm, rpm, rpd)` and the router tracks sliding-window counters per
entry. If a request would exceed any limit, that entry is skipped without a
network call. This complements (does not replace) the provider's own 429
handling — providers remain the source of truth.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from zetryn.auth.subscription import RateLimit

from .client import LLMClient
from .types import (
    LLMError,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
    Message,
    NoKeysAvailableError,
)

# Free-tier rate-limit presets, indexed by provider AND model.
#
# Rate limits differ PER MODEL — Gemini 2.5 Flash and Gemini 3.1 Flash Lite have
# different RPM/RPD; Groq's llama-3.1-8b-instant and qwen3-32b also differ.
# These numbers are pulled from public dashboards / docs at the time of writing
# and will drift. Treat as starting points, not contracts; override with real
# numbers from your own account whenever possible.
#
# Shape: provider_name -> { model_id -> RateLimit }.
# Use `get_free_tier_limit(provider, model)` to look up safely.
PROVIDER_FREE_TIER_LIMITS: dict[str, dict[str, RateLimit]] = {
    # Groq free tier — source: https://console.groq.com/docs/rate-limits
    "groq": {
        "llama-3.1-8b-instant":   RateLimit(rpm=30, rpd=14_400, tpm=6_000,  tpd=500_000),
        "llama-3.3-70b-versatile":RateLimit(rpm=30, rpd=1_000,  tpm=12_000, tpd=100_000),
        "meta-llama/llama-4-scout-17b-16e-instruct":
                                  RateLimit(rpm=30, rpd=1_000,  tpm=30_000, tpd=500_000),
        "openai/gpt-oss-120b":    RateLimit(rpm=30, rpd=1_000,  tpm=8_000,  tpd=200_000),
        "openai/gpt-oss-20b":     RateLimit(rpm=30, rpd=1_000,  tpm=8_000,  tpd=200_000),
        "qwen/qwen3-32b":         RateLimit(rpm=60, rpd=1_000,  tpm=6_000,  tpd=500_000),
        "groq/compound":          RateLimit(rpm=30, rpd=250,    tpm=70_000),
        "groq/compound-mini":     RateLimit(rpm=30, rpd=250,    tpm=70_000),
    },
    # Gemini free tier — source: Google AI Studio quota dashboard
    "gemini": {
        "gemini-2.5-flash":       RateLimit(rpm=5,  rpd=20,    tpm=250_000),
        "gemini-2.5-flash-lite":  RateLimit(rpm=10, rpd=20,    tpm=250_000),
        "gemini-3-flash":         RateLimit(rpm=5,  rpd=20,    tpm=250_000),
        "gemini-3.1-flash-lite":  RateLimit(rpm=15, rpd=500,   tpm=250_000),
        "gemini-3.5-flash":       RateLimit(rpm=5,  rpd=20,    tpm=250_000),
    },
    # OpenRouter free tier — source: https://openrouter.ai/docs/api/reference/limits
    # Free-tier models (":free" suffix) share a global limit: 20 RPM, 50 RPD
    # (200 RPD if account has ≥10 credits). No TPM cap; the per-model context
    # window is the practical limit.
    "openrouter": {
        ":free": RateLimit(rpm=20, rpd=50),
    },
}


def get_free_tier_limit(provider: str, model: str) -> RateLimit | None:
    """Look up a preset by provider + model. Returns None if unknown.

    For OpenRouter, any model ending in ":free" maps to the shared free-tier
    limit. For other providers, the model id must match exactly.
    """
    table = PROVIDER_FREE_TIER_LIMITS.get(provider)
    if table is None:
        return None
    if provider == "openrouter" and model.endswith(":free"):
        return table.get(":free")
    return table.get(model)


@dataclass
class _Throttle:
    """Sliding-window counters for one router entry."""

    limit: RateLimit | None = None
    _reqs_minute: deque[float] = field(default_factory=deque)
    _reqs_day: deque[float] = field(default_factory=deque)
    _tokens_minute: deque[tuple[float, int]] = field(default_factory=deque)
    _tokens_day: deque[tuple[float, int]] = field(default_factory=deque)

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def _evict(self, now: float) -> None:
        while self._reqs_minute and now - self._reqs_minute[0] >= 60.0:
            self._reqs_minute.popleft()
        while self._reqs_day and now - self._reqs_day[0] >= 86_400.0:
            self._reqs_day.popleft()
        while self._tokens_minute and now - self._tokens_minute[0][0] >= 60.0:
            self._tokens_minute.popleft()
        while self._tokens_day and now - self._tokens_day[0][0] >= 86_400.0:
            self._tokens_day.popleft()

    def can_request(self) -> bool:
        """Return True if a new request is allowed under current limits."""
        if self.limit is None:
            return True
        now = self._now()
        self._evict(now)
        lim = self.limit
        if lim.rpm is not None and len(self._reqs_minute) >= lim.rpm:
            return False
        if lim.rpd is not None and len(self._reqs_day) >= lim.rpd:
            return False
        if lim.tpm is not None:
            used = sum(t for _, t in self._tokens_minute)
            if used >= lim.tpm:
                return False
        if lim.tpd is not None:
            used_day = sum(t for _, t in self._tokens_day)
            if used_day >= lim.tpd:
                return False
        return True

    def record(self, tokens: int) -> None:
        """Record a successful request with its token usage."""
        if self.limit is None:
            return
        now = self._now()
        self._reqs_minute.append(now)
        self._reqs_day.append(now)
        self._tokens_minute.append((now, tokens))
        self._tokens_day.append((now, tokens))


@dataclass
class RouterEntry:
    """One provider in the router's failover chain."""

    client: LLMClient
    name: str = ""
    limit: RateLimit | None = None
    # When this entry is cooling down (monotonic), it is skipped.
    _cooldown_until: float = 0.0
    _throttle: _Throttle = field(init=False)

    def __post_init__(self) -> None:
        self._throttle = _Throttle(limit=self.limit)

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def available(self) -> bool:
        return self._cooldown_until <= self._now() and self._throttle.can_request()

    def penalize(self, cooldown_s: float) -> None:
        self._cooldown_until = self._now() + cooldown_s

    def record(self, tokens: int) -> None:
        self._throttle.record(tokens)


class LLMRouter:
    """Failover router that satisfies the `LLMClient` protocol."""

    def __init__(
        self,
        entries: list[RouterEntry | LLMClient],
        *,
        cooldown_s: float = 30.0,
    ) -> None:
        if not entries:
            raise ValueError("LLMRouter requires at least one entry")
        normalised: list[RouterEntry] = []
        for i, e in enumerate(entries):
            if isinstance(e, RouterEntry):
                normalised.append(e)
            else:
                normalised.append(RouterEntry(client=e, name=f"entry-{i}"))
        self._entries = normalised
        self._cooldown_s = cooldown_s

    @property
    def entries(self) -> list[RouterEntry]:
        return list(self._entries)

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        last_error: Exception | None = None
        tried = 0
        for entry in self._entries:
            if not entry.available():
                continue
            tried += 1
            try:
                result = await entry.client.complete(
                    messages,
                    model=model,
                    temperature=temperature,
                    json_mode=json_mode,
                    tools=tools,
                )
            except (LLMRateLimitError, NoKeysAvailableError) as exc:
                entry.penalize(self._cooldown_s)
                last_error = exc
                continue
            except LLMTimeoutError as exc:
                entry.penalize(self._cooldown_s)
                last_error = exc
                continue
            except LLMError as exc:
                last_error = exc
                continue

            tokens = (result.prompt_tokens or 0) + (result.completion_tokens or 0)
            entry.record(tokens)
            return result

        if tried == 0:
            raise NoKeysAvailableError(
                "all router entries are throttled or cooling down"
            )
        raise LLMError(f"router exhausted all providers: {last_error}")

    async def aclose(self) -> None:
        for entry in self._entries:
            close = getattr(entry.client, "aclose", None)
            if close is not None:
                await close()
