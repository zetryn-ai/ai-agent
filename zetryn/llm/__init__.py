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
from .structured import structured_complete
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
    "ZETRYN_API_BASE",
    "ZETRYN_MODELS",
    "KeyPool",
    "LLMClient",
    "LLMDecisionNode",
    "LLMError",
    "LLMNode",
    "LLMRateLimitError",
    "LLMResult",
    "LLMTimeoutError",
    "Message",
    "NoKeysAvailableError",
    "OpenAICompatibleClient",
    "ProviderConfig",
    "StructuredOutputError",
    "ZetrynClient",
    "assistant",
    "structured_complete",
    "system",
    "user",
]
