"""ZetrynClient — LLMClient backed by Zetryn's own models, gated by subscription.

This is how the product is consumed: a bot does ``import zetryn`` and uses
``ZetrynClient`` with its subscription key to run Zetryn models (Hardes/Medifus/
Easfus) in decide / advisor / hybrid modes.

Because everything implements ``LLMClient``, this drops into any graph unchanged.
Until the hosted platform is live, point ``base_url`` at a self-hosted vLLM/TGI
endpoint serving your fine-tuned model — the seam is identical.
"""

from __future__ import annotations

import os

import httpx

from ..auth import Entitlement, LocalSubscriptionAuth, SubscriptionAuth
from .config import ProviderConfig
from .openai_compat import OpenAICompatibleClient
from .types import LLMError, LLMResult, Message

# Hosted endpoint served by the Lema/Zetryn platform (placeholder until live).
ZETRYN_API_BASE = "https://api.zetryn.com/v1"

# Map friendly tier names to served model ids (analogous to opus/sonnet/haiku).
ZETRYN_MODELS = {
    "easfus": "zetryn-easfus",
    "medifus": "zetryn-medifus",
    "hardes": "zetryn-hardes",
}


class ZetrynClient:
    """An ``LLMClient`` for Zetryn models behind subscription auth.

    The inner HTTP client is built lazily, only after the subscription verifies —
    so an invalid subscription fails with a clear auth error, not a key-pool error.
    """

    def __init__(
        self,
        subscription_key: str | None,
        *,
        model: str = "medifus",
        base_url: str = ZETRYN_API_BASE,
        auth: SubscriptionAuth | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._sub_key = subscription_key
        self._model_tier = model
        self._base_url = base_url
        self._timeout_s = timeout_s
        self._auth = auth or LocalSubscriptionAuth()
        self._http = http_client
        self._entitlement: Entitlement | None = None
        self._inner: OpenAICompatibleClient | None = None

    @classmethod
    def from_env(
        cls,
        *,
        model: str = "medifus",
        env_var: str = "ZETRYN_API_KEY",
        **kwargs: object,
    ) -> ZetrynClient:
        """Build a client from a key in the environment (Groq/Gemini-style UX).

        The user generates the key at zetryn.com and sets ``ZETRYN_API_KEY``.
        """
        return cls(os.environ.get(env_var), model=model, **kwargs)  # type: ignore[arg-type]

    async def _ensure_ready(self) -> OpenAICompatibleClient:
        if self._inner is not None:
            return self._inner

        ent = await self._auth.verify(self._sub_key)
        if not ent.valid:
            raise LLMError(f"Zetryn subscription invalid: {ent.reason}")
        if self._model_tier not in ent.models:
            raise LLMError(
                f"model tier {self._model_tier!r} not included in your plan "
                f"({ent.tier}); allowed: {ent.models}"
            )
        self._entitlement = ent

        self._inner = OpenAICompatibleClient(
            ProviderConfig(
                name="zetryn",
                base_url=self._base_url,
                model=ZETRYN_MODELS.get(self._model_tier, self._model_tier),
                keys=[self._sub_key],  # subscription key doubles as bearer token
                timeout_s=self._timeout_s,
            ),
            http_client=self._http,
        )
        return self._inner

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        inner = await self._ensure_ready()
        served = ZETRYN_MODELS.get(model, model) if model else None
        return await inner.complete(
            messages, model=served, temperature=temperature, json_mode=json_mode
        )

    async def aclose(self) -> None:
        if self._inner is not None:
            await self._inner.aclose()
