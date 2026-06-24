"""Tests for the subscription auth seam + ZetrynClient."""

import httpx
import pytest

from zetryn.auth import Entitlement, License, LocalSubscriptionAuth
from zetryn.llm import LLMError, ZetrynClient, user

# -- auth seam ---------------------------------------------------------------


async def test_local_auth_rejects_empty_key():
    ent = await LocalSubscriptionAuth().verify(None)
    assert ent.valid is False
    assert "no subscription" in ent.reason


async def test_local_auth_grants_models():
    ent = await LocalSubscriptionAuth().verify("sub_abc")
    assert ent.valid is True
    assert "medifus" in ent.models


async def test_plan_presets_carry_limits():
    ent = await LocalSubscriptionAuth(plan="free").verify("sub_free")
    assert ent.tier == "free"
    assert ent.models == ["easfus"]
    assert ent.limits["easfus"].rpd == 200  # placeholder free-tier daily cap


async def test_pro_plan_includes_hardes():
    ent = await LocalSubscriptionAuth(plan="pro").verify("sub_pro")
    assert "hardes" in ent.models


# -- License (cached validation) ---------------------------------------------


async def test_license_caches_verification():
    calls = {"n": 0}

    class CountingAuth:
        async def verify(self, key):
            calls["n"] += 1
            return Entitlement(valid=True, tier="pro", models=["medifus"])

    lic = License("sub_x", auth=CountingAuth(), ttl_s=999)
    await lic.entitlement()
    await lic.entitlement()
    assert calls["n"] == 1  # second call served from cache


async def test_license_grace_on_auth_failure():
    state = {"fail": False}

    class FlakyAuth:
        async def verify(self, key):
            if state["fail"]:
                raise RuntimeError("auth down")
            return Entitlement(valid=True, tier="pro", models=["medifus"])

    lic = License("sub_x", auth=FlakyAuth(), ttl_s=0, grace_s=999)
    first = await lic.entitlement()
    assert first.valid
    state["fail"] = True
    # ttl=0 forces re-check; auth now fails, but grace keeps last good entitlement
    second = await lic.entitlement()
    assert second.valid is True


async def test_license_assert_active_raises_without_key():
    lic = License(None)
    with pytest.raises(PermissionError, match="subscription required"):
        await lic.assert_active()


# -- ZetrynClient ------------------------------------------------------------


def _model_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "zetryn-medifus",
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        },
    )


async def test_zetryn_client_completes_when_entitled():
    def handler(request: httpx.Request) -> httpx.Response:
        # subscription key is sent as the bearer token
        assert request.headers["Authorization"] == "Bearer sub_live_123"
        return _model_response("decision: buy")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ZetrynClient(
        "sub_live_123", model="medifus", base_url="https://test/v1", http_client=http
    )
    result = await client.complete([user("score this token")])
    assert result.text == "decision: buy"
    await http.aclose()


async def test_zetryn_client_rejects_invalid_subscription():
    client = ZetrynClient(None, model="medifus")  # no key
    with pytest.raises(LLMError, match="subscription invalid"):
        await client.complete([user("x")])


async def test_zetryn_client_rejects_model_not_in_plan():
    # plan only allows easfus, but client asks for hardes
    auth = LocalSubscriptionAuth(plan="free", models=("easfus",))
    client = ZetrynClient("sub_free", model="hardes", auth=auth)
    with pytest.raises(LLMError, match="not included in your plan"):
        await client.complete([user("x")])
