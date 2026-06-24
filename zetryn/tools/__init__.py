"""Generic tool machinery (chain-agnostic). Domain providers live in ``trading``."""

from .registry import ToolRegistry
from .tool import Tool, ToolResult, tool

__all__ = ["Tool", "ToolRegistry", "ToolResult", "tool"]
