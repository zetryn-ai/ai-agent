"""A registry of tools the caller injects for agent/LLM nodes to use."""

from __future__ import annotations

from typing import Any

from .tool import Tool, ToolResult


class ToolRegistry:
    """Holds named tools and runs them by name (safely)."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools or []:
            self.register(t)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name!r}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name!r}")
        return self._tools[name]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools)

    def specs(self) -> list[dict[str, Any]]:
        return [t.spec() for t in self._tools.values()]

    async def call(self, name: str, **kwargs: Any) -> ToolResult:
        if name not in self._tools:
            return ToolResult(ok=False, error=f"unknown tool: {name!r}")
        return await self._tools[name].call(**kwargs)
