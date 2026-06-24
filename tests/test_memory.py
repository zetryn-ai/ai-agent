"""Tests for the M4 memory layer."""

import asyncio

from zetryn.memory import Blacklist, DecisionLog, InMemoryStore, JSONFileStore


async def test_inmemory_put_get_delete():
    s = InMemoryStore()
    await s.put("ns", "k", {"v": 1})
    assert await s.get("ns", "k") == {"v": 1}
    await s.delete("ns", "k")
    assert await s.get("ns", "k") is None


async def test_inmemory_ttl_expiry():
    s = InMemoryStore()
    await s.put("ns", "k", "v", ttl=0.05)
    assert await s.get("ns", "k") == "v"
    await asyncio.sleep(0.06)
    assert await s.get("ns", "k") is None


async def test_query_returns_unexpired():
    s = InMemoryStore()
    await s.put("ns", "a", 1)
    await s.put("ns", "b", 2)
    assert sorted(await s.query("ns")) == [1, 2]


async def test_json_file_store_persists(tmp_path):
    path = tmp_path / "mem.json"
    s1 = JSONFileStore(path)
    await s1.put("ns", "k", {"x": 9})
    # New instance reading the same file sees the data.
    s2 = JSONFileStore(path)
    assert await s2.get("ns", "k") == {"x": 9}


async def test_blacklist():
    bl = Blacklist(InMemoryStore())
    assert not await bl.is_blacklisted("RUG")
    await bl.add("RUG", "mint authority active")
    assert await bl.is_blacklisted("RUG")
    assert await bl.reason("RUG") == "mint authority active"
    await bl.remove("RUG")
    assert not await bl.is_blacklisted("RUG")


async def test_decision_log_and_stats():
    log = DecisionLog(InMemoryStore())
    await log.log("run1", {"action": "alert", "confidence": 0.8})
    await log.log("run2", {"action": "skip", "confidence": 0.1})
    await log.record_outcome("run1", {"pnl": 1.5})

    stats = await log.stats()
    assert stats["total"] == 2
    assert stats["by_action"] == {"alert": 1, "skip": 1}
    assert stats["trades_with_outcome"] == 1
    assert stats["win_rate"] == 1.0
    assert stats["total_pnl"] == 1.5
