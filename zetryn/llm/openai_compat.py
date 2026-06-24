"""OpenAI-compatible LLM client.

One adapter covers Groq, OpenRouter, and Gemini's OpenAI-compatible endpoint —
they all speak the ``/chat/completions`` protocol. Differences are config only
(base_url, model, key env names).

Reliability: per-call key rotation on 429, exponential backoff on transient
errors, and a hard timeout so a slow provider can never hang a caller.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from .config import ProviderConfig
from .keypool import KeyPool
from .types import (
    LLMError,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
    Message,
    NoKeysAvailableError,
)


class OpenAICompatibleClient:
    """An LLM client speaking the OpenAI chat-completions protocol."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        key_pool: KeyPool | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._keys = key_pool or config.build_key_pool()
        self._http = http_client or httpx.AsyncClient(timeout=config.timeout_s)
        self._owns_http = http_client is None

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        cfg = self._config
        payload: dict = {
            "model": model or cfg.model,
            "messages": messages,
            "temperature": cfg.temperature if temperature is None else temperature,
        }
        if json_mode and cfg.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}

        url = f"{cfg.base_url.rstrip('/')}/chat/completions"
        rotations = 0
        last_error: Exception | None = None

        for attempt in range(cfg.max_retries):
            try:
                key = self._keys.acquire()
            except NoKeysAvailableError as exc:
                # Wait a short, bounded time then retry acquiring.
                last_error = exc
                await asyncio.sleep(min(2.0 * (attempt + 1), 5.0))
                continue

            headers = {"Authorization": f"Bearer {key}"}
            t0 = time.perf_counter()
            try:
                resp = await self._http.post(url, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                last_error = LLMTimeoutError(str(exc))
                await self._backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                last_error = LLMError(f"transport error: {exc}")
                await self._backoff(attempt)
                continue

            if resp.status_code == 429:
                self._keys.penalize(key)
                rotations += 1
                last_error = LLMRateLimitError("429 rate limited")
                await self._backoff(attempt)
                continue
            if resp.status_code >= 500:
                last_error = LLMError(f"provider {resp.status_code}")
                await self._backoff(attempt)
                continue
            if resp.status_code >= 400:
                raise LLMError(f"provider error {resp.status_code}: {resp.text[:300]}")

            data = resp.json()
            latency_ms = (time.perf_counter() - t0) * 1000
            return self._parse(data, model or cfg.model, latency_ms, rotations)

        raise LLMError(
            f"completion failed after {cfg.max_retries} attempts: {last_error}"
        )

    @staticmethod
    def _parse(data: dict, model: str, latency_ms: float, rotations: int) -> LLMResult:
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected response shape: {exc}") from exc
        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            model=data.get("model", model),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            key_rotations=rotations,
            raw=data,
        )

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep(min(0.5 * (2**attempt), 8.0))

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()
