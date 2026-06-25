"""Tests for K1 (KOL schemas) and K2 (KOLRegistry from KnowledgePack)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from strategies import KOLRegistry
from trading import (
    KOLBuyEvent,
    KOLContext,
    KOLCopyTradeConfig,
    KOLProfile,
    TokenInput,
)
from zetryn.knowledge import KnowledgePack


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# -- K1: KOL schemas --------------------------------------------------------


def test_kol_profile_defaults_are_safe():
    p = KOLProfile()
    assert p.hit_rate == 0.0
    assert p.tier == "C"
    assert p.min_sol_to_copy == 0.0


def test_kol_profile_validates_hit_rate_range():
    with pytest.raises(ValidationError):
        KOLProfile(hit_rate=1.5)
    with pytest.raises(ValidationError):
        KOLProfile(hit_rate=-0.1)


def test_kol_buy_event_required_fields():
    e = KOLBuyEvent(
        wallet="abc", mint="def", sol_amount=0.5,
        detected_at_ts=1000.0, block_age_seconds=5.0,
    )
    assert e.wallet == "abc"
    assert e.sol_amount == 0.5


def test_kol_buy_event_rejects_negative_size():
    with pytest.raises(ValidationError):
        KOLBuyEvent(
            wallet="x", mint="y", sol_amount=-1.0,
            detected_at_ts=0, block_age_seconds=0,
        )


def test_kol_copytrade_config_defaults():
    cfg = KOLCopyTradeConfig()
    assert cfg.decision_mode == "rule"
    assert cfg.min_kol_tier == "A"
    assert cfg.kol_cooldown_seconds == 60.0
    assert cfg.kol_confidence_floor < cfg.kol_confidence_ceiling


def test_kol_copytrade_config_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        KOLCopyTradeConfig(decision_mode="bogus")


def test_kol_context_round_trip():
    ctx = KOLContext(
        event=KOLBuyEvent(
            wallet="W", mint="M", sol_amount=0.3,
            detected_at_ts=1000.0, block_age_seconds=2.0,
        ),
        token=TokenInput(mint="M", symbol="MEME", name="Meme"),
    )
    assert ctx.event.wallet == "W"
    assert ctx.token.symbol == "MEME"
    assert ctx.last_copy_ts is None
    assert ctx.config.decision_mode == "rule"


# -- K2: KOLRegistry --------------------------------------------------------


def _seed_pack(root: Path, wallets: dict, **globals_):
    _write(
        root / "data" / "kol_whitelist.json",
        json.dumps({"wallets": wallets, **globals_}),
    )
    return KnowledgePack.from_dir(root)


def test_registry_empty_when_pack_has_no_whitelist(tmp_path):
    pack = KnowledgePack.from_dir(tmp_path)  # no data/ dir at all
    reg = KOLRegistry.from_pack(pack)
    assert len(reg) == 0
    assert not reg
    assert reg.get("anything") is None
    assert not reg.is_known("anything")


def test_registry_loads_profiles_with_global_floor(tmp_path):
    pack = _seed_pack(
        tmp_path,
        wallets={
            "ABC": {"name": "smart_money_1", "hit_rate": 0.55, "tier": "S"},
            "DEF": {"name": "decent", "hit_rate": 0.45, "tier": "A"},
        },
        min_tier_to_copy="A",
        min_hit_rate=0.40,
    )
    reg = KOLRegistry.from_pack(pack)
    assert len(reg) == 2
    assert reg.is_known("ABC")
    assert reg.min_tier == "A"
    assert reg.min_hit_rate == 0.40
    abc = reg.get("ABC")
    assert abc is not None and abc.hit_rate == 0.55 and abc.tier == "S"


def test_registry_passes_global_floor_logic(tmp_path):
    pack = _seed_pack(
        tmp_path,
        wallets={
            "S1":  {"hit_rate": 0.60, "tier": "S"},
            "A1":  {"hit_rate": 0.45, "tier": "A"},
            "B1":  {"hit_rate": 0.55, "tier": "B"},   # tier too low
            "A2":  {"hit_rate": 0.30, "tier": "A"},   # hit_rate too low
        },
        min_tier_to_copy="A",
        min_hit_rate=0.40,
    )
    reg = KOLRegistry.from_pack(pack)
    assert reg.passes_global_floor(reg.get("S1")) is True
    assert reg.passes_global_floor(reg.get("A1")) is True
    assert reg.passes_global_floor(reg.get("B1")) is False  # tier B fails
    assert reg.passes_global_floor(reg.get("A2")) is False  # hit_rate fails


def test_registry_uses_permissive_defaults_when_globals_missing(tmp_path):
    pack = _seed_pack(tmp_path, wallets={"X": {"hit_rate": 0.5, "tier": "C"}})
    reg = KOLRegistry.from_pack(pack)
    # No min_tier_to_copy / min_hit_rate in JSON → very permissive defaults
    assert reg.min_tier == "C"
    assert reg.min_hit_rate == 0.0
    assert reg.passes_global_floor(reg.get("X")) is True


def test_registry_skips_malformed_profile_entries(tmp_path):
    pack = _seed_pack(
        tmp_path,
        wallets={
            "GOOD": {"hit_rate": 0.5, "tier": "S"},
            "BAD":  "not even a dict",
        },
    )
    reg = KOLRegistry.from_pack(pack)
    # Malformed entry is silently dropped — registry stays useful
    assert "GOOD" in reg
    assert "BAD" not in reg


def test_registry_contains_and_len_dunders(tmp_path):
    pack = _seed_pack(
        tmp_path,
        wallets={"A": {"hit_rate": 0.5, "tier": "A"}, "B": {"hit_rate": 0.5, "tier": "B"}},
    )
    reg = KOLRegistry.from_pack(pack)
    assert "A" in reg
    assert "Z" not in reg
    assert len(reg) == 2


def test_registry_as_dict_for_debug(tmp_path):
    pack = _seed_pack(
        tmp_path,
        wallets={"X": {"name": "x", "hit_rate": 0.5, "tier": "S"}},
        min_tier_to_copy="A",
        min_hit_rate=0.4,
    )
    reg = KOLRegistry.from_pack(pack)
    dump = reg.as_dict()
    assert dump["min_tier"] == "A"
    assert dump["wallets"]["X"]["tier"] == "S"
