"""Filesystem-backed knowledge pack loader.

Layout (all keys optional — missing subdirs are ignored):

    pack_dir/
        system/                 # *.md → system-prompt blocks, sorted by filename
            01-trading-rules.md
            02-risk-policy.md
        data/                   # *.json → structured lookups
            kol-whitelist.json
            blacklist-tokens.json

The pack is loaded eagerly and held in memory — it is meant for facts that do
not change during a run (rules, whitelists, lessons compiled offline). Use the
`MemoryStore` for things that mutate during a run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zetryn.llm.types import Message, system


class KnowledgePackError(Exception):
    """Raised when a pack cannot be loaded (missing dir, bad JSON, etc.)."""


@dataclass
class KnowledgePack:
    """An immutable bundle of static knowledge loaded from a directory.

    Use `KnowledgePack.from_dir(path)` to construct one. The default
    constructor is exposed for tests and in-memory packs.
    """

    blocks: list[tuple[str, str]] = field(default_factory=list)
    # filename (without extension) -> top-level JSON value
    data: dict[str, Any] = field(default_factory=dict)

    # -- Loading -----------------------------------------------------------

    @classmethod
    def from_dir(cls, path: str | Path) -> KnowledgePack:
        root = Path(path)
        if not root.is_dir():
            raise KnowledgePackError(f"knowledge pack dir not found: {root}")

        blocks: list[tuple[str, str]] = []
        system_dir = root / "system"
        if system_dir.is_dir():
            for md in sorted(system_dir.glob("*.md")):
                text = md.read_text(encoding="utf-8").strip()
                if text:
                    blocks.append((md.stem, text))

        data: dict[str, Any] = {}
        data_dir = root / "data"
        if data_dir.is_dir():
            for jf in sorted(data_dir.glob("*.json")):
                try:
                    data[jf.stem] = json.loads(jf.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise KnowledgePackError(
                        f"invalid JSON in {jf}: {exc}"
                    ) from exc

        return cls(blocks=blocks, data=data)

    # -- System prompt surface --------------------------------------------

    def system_blocks(self) -> list[Message]:
        """One system message per markdown file, in filename order."""
        return [system(text) for _, text in self.blocks]

    def as_system_message(self) -> Message | None:
        """All markdown blocks merged into a single system message.

        Returns None if the pack has no markdown content — caller decides
        whether to skip injection or raise.
        """
        if not self.blocks:
            return None
        body = "\n\n---\n\n".join(text for _, text in self.blocks)
        return system(body)

    # -- Structured lookup ------------------------------------------------

    def namespaces(self) -> list[str]:
        """List the JSON namespaces (one per file under data/)."""
        return list(self.data.keys())

    def lookup(self, ns: str, key: str | None = None, default: Any = None) -> Any:
        """Look up structured data.

        - `lookup("kol-whitelist")` → the whole parsed JSON value.
        - `lookup("kol-whitelist", "wallets")` → `data["wallets"]` from that file.
        - Returns `default` if the namespace or key is missing.
        """
        if ns not in self.data:
            return default
        value = self.data[ns]
        if key is None:
            return value
        if isinstance(value, dict):
            return value.get(key, default)
        return default

    # -- Introspection ----------------------------------------------------

    def __len__(self) -> int:
        return len(self.blocks) + len(self.data)

    def __bool__(self) -> bool:
        return bool(self.blocks) or bool(self.data)
