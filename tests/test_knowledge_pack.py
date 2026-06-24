"""Tests for KnowledgePack (markdown + JSON loader)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zetryn.knowledge import KnowledgePack, KnowledgePackError


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# -- Loading ---------------------------------------------------------------


def test_from_dir_missing_raises(tmp_path: Path):
    with pytest.raises(KnowledgePackError):
        KnowledgePack.from_dir(tmp_path / "nope")


def test_from_dir_empty_dir_yields_empty_pack(tmp_path: Path):
    pack = KnowledgePack.from_dir(tmp_path)
    assert not pack
    assert pack.system_blocks() == []
    assert pack.as_system_message() is None
    assert pack.namespaces() == []


def test_from_dir_loads_markdown_in_filename_order(tmp_path: Path):
    _write(tmp_path / "system" / "02-second.md", "second block")
    _write(tmp_path / "system" / "01-first.md", "first block")
    pack = KnowledgePack.from_dir(tmp_path)
    blocks = pack.system_blocks()
    assert [m["content"] for m in blocks] == ["first block", "second block"]
    assert all(m["role"] == "system" for m in blocks)


def test_from_dir_skips_empty_markdown(tmp_path: Path):
    _write(tmp_path / "system" / "a.md", "   \n  \n")
    _write(tmp_path / "system" / "b.md", "real content")
    pack = KnowledgePack.from_dir(tmp_path)
    assert len(pack.system_blocks()) == 1


def test_from_dir_loads_json_data(tmp_path: Path):
    payload = {"wallets": ["AAA", "BBB"], "min_score": 0.8}
    _write(tmp_path / "data" / "kol-whitelist.json", json.dumps(payload))
    pack = KnowledgePack.from_dir(tmp_path)
    assert pack.namespaces() == ["kol-whitelist"]
    assert pack.lookup("kol-whitelist") == payload
    assert pack.lookup("kol-whitelist", "wallets") == ["AAA", "BBB"]
    assert pack.lookup("kol-whitelist", "missing", default="x") == "x"


def test_from_dir_bad_json_raises(tmp_path: Path):
    _write(tmp_path / "data" / "broken.json", "{not valid")
    with pytest.raises(KnowledgePackError):
        KnowledgePack.from_dir(tmp_path)


# -- API surfaces ----------------------------------------------------------


def test_as_system_message_joins_with_separator(tmp_path: Path):
    _write(tmp_path / "system" / "01.md", "rule A")
    _write(tmp_path / "system" / "02.md", "rule B")
    pack = KnowledgePack.from_dir(tmp_path)
    msg = pack.as_system_message()
    assert msg is not None
    assert msg["role"] == "system"
    assert msg["content"] == "rule A\n\n---\n\nrule B"


def test_lookup_unknown_namespace_returns_default():
    pack = KnowledgePack(data={"a": {"k": 1}})
    assert pack.lookup("ghost") is None
    assert pack.lookup("ghost", default="d") == "d"


def test_lookup_key_on_non_dict_returns_default():
    pack = KnowledgePack(data={"list-only": [1, 2, 3]})
    assert pack.lookup("list-only") == [1, 2, 3]
    assert pack.lookup("list-only", "key") is None
    assert pack.lookup("list-only", "key", default="fallback") == "fallback"


def test_len_and_bool_reflect_content():
    empty = KnowledgePack()
    assert not empty and len(empty) == 0

    with_blocks = KnowledgePack(blocks=[("a", "x")])
    assert with_blocks and len(with_blocks) == 1

    with_both = KnowledgePack(blocks=[("a", "x")], data={"n": {}})
    assert len(with_both) == 2


# -- Integration: real round-trip -----------------------------------------


def test_full_pack_round_trip(tmp_path: Path):
    _write(
        tmp_path / "system" / "01-trading-rules.md",
        "Never long during ATH unless funding is negative.",
    )
    _write(
        tmp_path / "system" / "02-risk-policy.md",
        "Max 2% risk per trade. Stop loss is mandatory.",
    )
    _write(
        tmp_path / "data" / "blacklist.json",
        json.dumps({"tokens": ["RUG1", "RUG2"], "devs": ["dev-abc"]}),
    )
    pack = KnowledgePack.from_dir(tmp_path)

    assert len(pack.system_blocks()) == 2
    assert pack.lookup("blacklist", "tokens") == ["RUG1", "RUG2"]
    assert "trading-rules" in pack.blocks[0][0]
