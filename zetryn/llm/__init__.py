"""LLM layer: provider-agnostic advisor calls with structured output."""

from .client import LLMClient
from .config import (
    GEMINI_BASE_URL,
    GROQ_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    ProviderConfig,
)
from .keypool import KeyPool
from .node import LLMDecisionNode, LLMNode
from .openai_compat import OpenAICompatibleClient
from .router import (
    PROVIDER_FREE_TIER_LIMITS,
    LLMRouter,
    RouterEntry,
    get_free_tier_limit,
)
from .structured import structured_complete
from .tool_use import ToolUseNode, ToolUseTrace, tool_use_loop
from .types import (
    LLMError,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
    Message,
    NoKeysAvailableError,
    StructuredOutputError,
    assistant,
    system,
    user,
)
from .zetryn_client import ZETRYN_API_BASE, ZETRYN_MODELS, ZetrynClient

__all__ = [
    "GEMINI_BASE_URL",
    "GROQ_BASE_URL",
    "OPENAI_BASE_URL",
    "OPENROUTER_BASE_URL",
    "PROVIDER_FREE_TIER_LIMITS",
    "ZETRYN_API_BASE",
    "ZETRYN_MODELS",
    "KeyPool",
    "LLMClient",
    "LLMDecisionNode",
    "LLMError",
    "LLMNode",
    "LLMRateLimitError",
    "LLMResult",
    "LLMRouter",
    "LLMTimeoutError",
    "Message",
    "NoKeysAvailableError",
    "OpenAICompatibleClient",
    "ProviderConfig",
    "RouterEntry",
    "StructuredOutputError",
    "ToolUseNode",
    "ToolUseTrace",
    "ZetrynClient",
    "assistant",
    "get_free_tier_limit",
    "structured_complete",
    "system",
    "tool_use_loop",
    "user",
]
